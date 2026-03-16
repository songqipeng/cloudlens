#!/usr/bin/env bash
# 删除香港区（ap-east-1）所有 CloudLens 相关 AWS 资源，将消费压到最低。
# 使用前请确保已配置 AWS CLI 且具有相应权限。
# 用法: ./scripts/aws-delete-all-hongkong.sh
set -e
REGION="ap-east-1"
INSTANCE_ID="i-093e75d2cc47bdc7f"
ALB_NAME="cloudlens-alb-v2"

echo "===== 香港区（$REGION）资源清理 ====="

# 1. 删除 ALB（先删监听器再删 ALB，目标组在 ALB 删除后可删）
ALB_ARN=$(aws elbv2 describe-load-balancers --region "$REGION" --names "$ALB_NAME" --query 'LoadBalancers[0].LoadBalancerArn' --output text 2>/dev/null || true)
if [[ -n "$ALB_ARN" && "$ALB_ARN" != "None" ]]; then
  echo "[1/7] 删除 ALB 监听器与 ALB: $ALB_NAME"
  for LARN in $(aws elbv2 describe-listeners --region "$REGION" --load-balancer-arn "$ALB_ARN" --query 'Listeners[*].ListenerArn' --output text 2>/dev/null); do
    aws elbv2 delete-listener --region "$REGION" --listener-arn "$LARN" && echo "  已删监听器 $LARN"
  done
  aws elbv2 delete-load-balancer --region "$REGION" --load-balancer-arn "$ALB_ARN" && echo "  已删 ALB $ALB_NAME"
else
  echo "[1/7] 未找到 ALB $ALB_NAME，跳过"
fi

# 2. 删除目标组（名称带 cloudlens 的；需在 ALB 删除后执行）
echo "[2/7] 删除 CloudLens 目标组"
for TG_ARN in $(aws elbv2 describe-target-groups --region "$REGION" --query 'TargetGroups[*].TargetGroupArn' --output text 2>/dev/null); do
  name=$(aws elbv2 describe-target-groups --region "$REGION" --target-group-arns "$TG_ARN" --query 'TargetGroups[0].TargetGroupName' --output text 2>/dev/null)
  if [[ "$name" == *cloudlens* ]]; then
    aws elbv2 delete-target-group --region "$REGION" --target-group-arn "$TG_ARN" && echo "  已删目标组 $name"
  fi
done

# 3. 终止 EC2 实例
echo "[3/7] 终止 EC2 实例 $INSTANCE_ID"
if aws ec2 describe-instances --region "$REGION" --instance-ids "$INSTANCE_ID" --query 'Reservations[*].Instances[*].State.Name' --output text 2>/dev/null | grep -q 'running\|pending\|stopping\|stopped'; then
  aws ec2 terminate-instances --region "$REGION" --instance-ids "$INSTANCE_ID" && echo "  已发起终止"
else
  echo "  实例不存在或已终止，跳过"
fi

# 4. 等待实例终止（以便 EBS 可删）
echo "[4/7] 等待实例终止（最多 120 秒）"
aws ec2 wait instance-terminated --region "$REGION" --instance-ids "$INSTANCE_ID" 2>/dev/null && echo "  实例已终止" || echo "  等待超时或实例已不存在，继续"

# 5. 删除 EBS 卷（根卷可能在终止时已删，按 DeleteOnTermination；数据卷需手动删）
echo "[5/7] 删除 EBS 卷"
for VOL_ID in $(aws ec2 describe-volumes --region "$REGION" --filters "Name=tag:Name,Values=*cloudlens*" --query 'Volumes[*].VolumeId' --output text 2>/dev/null); do
  STATE=$(aws ec2 describe-volumes --region "$REGION" --volume-ids "$VOL_ID" --query 'Volumes[0].State' --output text 2>/dev/null)
  if [[ "$STATE" == "available" ]]; then
    aws ec2 delete-volume --region "$REGION" --volume-id "$VOL_ID" && echo "  已删卷 $VOL_ID"
  else
    echo "  卷 $VOL_ID 状态 $STATE，稍后可在控制台手动删除"
  fi
done
# 已知香港卷 ID（若上面按 tag 没扫到）
for VOL_ID in vol-09f3aa71c4e5cb36e vol-038fa05d79951604c; do
  STATE=$(aws ec2 describe-volumes --region "$REGION" --volume-ids "$VOL_ID" --query 'Volumes[0].State' --output text 2>/dev/null) || true
  if [[ "$STATE" == "available" ]]; then
    aws ec2 delete-volume --region "$REGION" --volume-id "$VOL_ID" && echo "  已删卷 $VOL_ID"
  fi
done

# 6. 释放未关联的弹性 IP
echo "[6/7] 释放未关联的弹性 IP"
for ALLOC in $(aws ec2 describe-addresses --region "$REGION" --query 'Addresses[?AssociationId==null].AllocationId' --output text 2>/dev/null); do
  aws ec2 release-address --region "$REGION" --allocation-id "$ALLOC" && echo "  已释放 $ALLOC"
done

# 7. 删除 CloudLens 安全组（需在 ALB 与 EC2 删除后）
echo "[7/7] 删除 CloudLens 安全组与日志组"
for SG in cloudlens-alb-sg cloudlens-ec2-sg; do
  SG_ID=$(aws ec2 describe-security-groups --region "$REGION" --filters "Name=group-name,Values=$SG" --query 'SecurityGroups[0].GroupId' --output text 2>/dev/null)
  if [[ -n "$SG_ID" && "$SG_ID" != "None" ]]; then
    aws ec2 delete-security-group --region "$REGION" --group-id "$SG_ID" 2>/dev/null && echo "  已删安全组 $SG" || echo "  安全组 $SG 仍被引用，可稍后在控制台删除"
  fi
done
LOG_GROUP="/aws/ec2/cloudlens-v2"
aws logs delete-log-group --region "$REGION" --log-group-name "$LOG_GROUP" 2>/dev/null && echo "  已删日志组 $LOG_GROUP" || true

echo "===== 香港区资源清理完成 ====="
echo "建议：在控制台确认 ap-east-1 无 EC2/ALB/EBS/EIP 等残留；密钥对、IAM 角色等不产生持续费用，可按需保留或删除。"
