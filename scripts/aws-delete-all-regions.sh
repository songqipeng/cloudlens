#!/usr/bin/env bash
# 删除所有区域可能产生费用的 AWS 资源（EC2/EBS/ELB/NAT/EIP/RDS/Lambda/ECS/ElastiCache/CloudWatch Logs 等）。
# 不删除：默认 VPC、IAM、密钥对（不产生持续费用）。S3 需先清空再删桶。
# 使用前请确保已配置 AWS CLI 且具有相应权限。建议先 --dry-run 查看将删除项。
# 用法: ./scripts/aws-delete-all-regions.sh [--dry-run]
set -e
DRY_RUN=false
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=true

run_cmd() {
  if $DRY_RUN; then echo "[DRY-RUN] $*"; else "$@"; fi
}

delete_in_region() {
  local REGION="$1"
  echo "-------- 区域 $REGION --------"

  # 1. NAT 网关（费用高，先删）
  for nat in $(aws ec2 describe-nat-gateways --region "$REGION" --query 'NatGateways[?State!=`deleted`].NatGatewayId' --output text 2>/dev/null); do
    echo "  删除 NAT 网关 $nat"
    run_cmd aws ec2 delete-nat-gateway --region "$REGION" --nat-gateway-id "$nat" 2>/dev/null || true
  done

  # 2. 负载均衡：先删监听器，再删 ALB/NLB，再删目标组
  for lb_arn in $(aws elbv2 describe-load-balancers --region "$REGION" --query 'LoadBalancers[*].LoadBalancerArn' --output text 2>/dev/null); do
    for larn in $(aws elbv2 describe-listeners --region "$REGION" --load-balancer-arn "$lb_arn" --query 'Listeners[*].ListenerArn' --output text 2>/dev/null); do
      run_cmd aws elbv2 delete-listener --region "$REGION" --listener-arn "$larn" 2>/dev/null || true
    done
    run_cmd aws elbv2 delete-load-balancer --region "$REGION" --load-balancer-arn "$lb_arn" 2>/dev/null || true
  done
  for tg_arn in $(aws elbv2 describe-target-groups --region "$REGION" --query 'TargetGroups[*].TargetGroupArn' --output text 2>/dev/null); do
    run_cmd aws elbv2 delete-target-group --region "$REGION" --target-group-arn "$tg_arn" 2>/dev/null || true
  done

  # 3. 终止所有 EC2 实例（含 running/stopped）
  for iid in $(aws ec2 describe-instances --region "$REGION" --query 'Reservations[*].Instances[*].InstanceId' --output text 2>/dev/null); do
    state=$(aws ec2 describe-instances --region "$REGION" --instance-ids "$iid" --query 'Reservations[0].Instances[0].State.Name' --output text 2>/dev/null)
    if [[ "$state" == "running" || "$state" == "pending" || "$state" == "stopped" || "$state" == "stopping" ]]; then
      echo "  终止实例 $iid ($state)"
      run_cmd aws ec2 terminate-instances --region "$REGION" --instance-ids "$iid" 2>/dev/null || true
    fi
  done

  # 4. RDS 实例（删除且跳过最终快照以省成本，可改为 --no-skip-final-snapshot 保留）
  for db in $(aws rds describe-db-instances --region "$REGION" --query 'DBInstances[*].DBInstanceIdentifier' --output text 2>/dev/null); do
    echo "  删除 RDS $db"
    run_cmd aws rds delete-db-instance --region "$REGION" --db-instance-identifier "$db" --skip-final-snapshot 2>/dev/null || true
  done

  # 5. Lambda 函数
  for func in $(aws lambda list-functions --region "$REGION" --query 'Functions[*].FunctionName' --output text 2>/dev/null); do
    echo "  删除 Lambda $func"
    run_cmd aws lambda delete-function --region "$REGION" --function-name "$func" 2>/dev/null || true
  done

  # 6. ECS 服务与集群（先停服务再删集群）
  for cluster in $(aws ecs list-clusters --region "$REGION" --query 'clusterArns[*]' --output text 2>/dev/null); do
    for svc in $(aws ecs list-services --region "$REGION" --cluster "$cluster" --query 'serviceArns[*]' --output text 2>/dev/null); do
      run_cmd aws ecs update-service --region "$REGION" --cluster "$cluster" --service "$svc" --desired-count 0 2>/dev/null || true
      run_cmd aws ecs delete-service --region "$REGION" --cluster "$cluster" --service "$svc" --force 2>/dev/null || true
    done
    run_cmd aws ecs delete-cluster --region "$REGION" --cluster "$cluster" 2>/dev/null || true
  done

  # 7. ElastiCache 复制组与集群
  for rg in $(aws elasticache describe-replication-groups --region "$REGION" --query 'ReplicationGroups[*].ReplicationGroupId' --output text 2>/dev/null); do
    echo "  删除 ElastiCache 复制组 $rg"
    run_cmd aws elasticache delete-replication-group --region "$REGION" --replication-group-id "$rg" 2>/dev/null || true
  done
  for cache in $(aws elasticache describe-cache-clusters --region "$REGION" --query 'CacheClusters[*].CacheClusterId' --output text 2>/dev/null); do
    echo "  删除 ElastiCache 集群 $cache"
    run_cmd aws elasticache delete-cache-cluster --region "$REGION" --cache-cluster-id "$cache" 2>/dev/null || true
  done

  # 7b. DynamoDB 表
  for table in $(aws dynamodb list-tables --region "$REGION" --query 'TableNames[*]' --output text 2>/dev/null); do
    echo "  删除 DynamoDB 表 $table"
    run_cmd aws dynamodb delete-table --region "$REGION" --table-name "$table" 2>/dev/null || true
  done

  # 8. 等待本区域实例终止后再删卷与 EIP（最多等 2 分钟/实例）
  if ! $DRY_RUN; then
    for iid in $(aws ec2 describe-instances --region "$REGION" --filters "Name=instance-state-name,Values=pending,running,stopping" --query 'Reservations[*].Instances[*].InstanceId' --output text 2>/dev/null); do
      aws ec2 wait instance-terminated --region "$REGION" --instance-ids "$iid" --max-attempts 24 2>/dev/null || true
    done
  fi

  # 9. 删除可用状态的 EBS 卷
  for vol in $(aws ec2 describe-volumes --region "$REGION" --filters "Name=status,Values=available" --query 'Volumes[*].VolumeId' --output text 2>/dev/null); do
    echo "  删除 EBS 卷 $vol"
    run_cmd aws ec2 delete-volume --region "$REGION" --volume-id "$vol" 2>/dev/null || true
  done

  # 10. 释放未关联的弹性 IP
  for alloc in $(aws ec2 describe-addresses --region "$REGION" --query 'Addresses[?AssociationId==null].AllocationId' --output text 2>/dev/null); do
    run_cmd aws ec2 release-address --region "$REGION" --allocation-id "$alloc" 2>/dev/null || true
  done

  # 11. CloudWatch Logs 日志组（会产生存储费用）
  for lg in $(aws logs describe-log-groups --region "$REGION" --query 'logGroups[*].logGroupName' --output text 2>/dev/null); do
    echo "  删除日志组 $lg"
    run_cmd aws logs delete-log-group --region "$REGION" --log-group-name "$lg" 2>/dev/null || true
  done

  # 12. 删除非默认安全组（可选，可能被其他资源引用导致失败）
  default_vpc=$(aws ec2 describe-vpcs --region "$REGION" --filters "Name=isDefault,Values=true" --query 'Vpcs[0].VpcId' --output text 2>/dev/null)
  for sg in $(aws ec2 describe-security-groups --region "$REGION" --query 'SecurityGroups[?GroupName!=`default`].GroupId' --output text 2>/dev/null); do
    run_cmd aws ec2 delete-security-group --region "$REGION" --group-id "$sg" 2>/dev/null || true
  done
}

echo "===== 全区域可能产生费用的资源清理 ====="
if $DRY_RUN; then echo "（仅打印将要执行的操作，不实际删除）"; fi

REGIONS=$(aws ec2 describe-regions --query 'Regions[*].RegionName' --output text 2>/dev/null)
for r in $REGIONS; do
  delete_in_region "$r" || true
done

# S3 桶（全局）：清空后删除
echo "-------- S3 桶（全局）--------"
for bucket in $(aws s3api list-buckets --query 'Buckets[*].Name' --output text 2>/dev/null); do
  echo "  清空并删除桶 $bucket"
  run_cmd aws s3 rm "s3://$bucket/" --recursive 2>/dev/null || true
  run_cmd aws s3api delete-bucket --bucket "$bucket" 2>/dev/null || true
done

echo "===== 全区域资源清理完成 ====="
echo "建议：在控制台 Cost Explorer 或各区域确认无 EC2/ELB/EBS/RDS/Lambda/ECS/S3 等残留。"
echo "NAT 网关删除后需数分钟才能释放，EIP 可能在 NAT 删除后自动释放或需手动释放。"
