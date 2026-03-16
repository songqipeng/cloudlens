#!/usr/bin/env bash
# 检查所有区域是否还有可能产生费用的资源（用于确认「全删」后是否干净）。
# 用法: ./scripts/aws-check-billable-resources.sh
set -e
REGIONS=$(aws ec2 describe-regions --query 'Regions[*].RegionName' --output text 2>/dev/null)
FOUND=0

check() {
  local name="$1"
  local out
  out=$(eval "$2" 2>/dev/null)
  if [[ -n "$out" ]]; then
    echo "[有] $name: $out"
    FOUND=$((FOUND + 1))
  fi
}

echo "===== 检查可能产生费用的资源 ====="
for r in $REGIONS; do
  check "EC2($r)" "aws ec2 describe-instances --region $r --filters Name=instance-state-name,Values=pending,running,stopping,stopped --query 'Reservations[*].Instances[*].InstanceId' --output text"
  check "EBS($r)" "aws ec2 describe-volumes --region $r --query 'Volumes[*].VolumeId' --output text"
  check "ELB($r)" "aws elbv2 describe-load-balancers --region $r --query 'LoadBalancers[*].LoadBalancerName' --output text"
  check "NAT($r)" "aws ec2 describe-nat-gateways --region $r --query \"NatGateways[?State!=\\\`deleted\\\`].NatGatewayId\" --output text"
  check "EIP($r)" "aws ec2 describe-addresses --region $r --query 'Addresses[*].AllocationId' --output text"
  check "RDS($r)" "aws rds describe-db-instances --region $r --query 'DBInstances[*].DBInstanceIdentifier' --output text"
  check "Lambda($r)" "aws lambda list-functions --region $r --query 'Functions[*].FunctionName' --output text"
  check "ECS($r)" "aws ecs list-clusters --region $r --query 'clusterArns[*]' --output text"
  check "DynamoDB($r)" "aws dynamodb list-tables --region $r --query 'TableNames[*]' --output text"
  check "Logs($r)" "aws logs describe-log-groups --region $r --query 'logGroups[*].logGroupName' --output text"
done
check "S3(全局)" "aws s3api list-buckets --query 'Buckets[*].Name' --output text"

if [[ $FOUND -eq 0 ]]; then
  echo "[结果] 未发现可能产生费用的资源，已全部清理。"
else
  echo "[结果] 发现 $FOUND 类资源，请到控制台或使用 aws-delete-all-regions.sh 清理。"
fi
