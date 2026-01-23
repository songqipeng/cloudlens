output "instance_id" {
  description = "EC2实例ID"
  value       = aws_instance.cloudlens.id
}

output "instance_public_ip" {
  description = "EC2实例公网IP"
  value       = aws_instance.cloudlens.public_ip
}

output "instance_private_ip" {
  description = "EC2实例私网IP"
  value       = aws_instance.cloudlens.private_ip
}

output "alb_dns_name" {
  description = "Application Load Balancer DNS名称"
  value       = aws_lb.cloudlens.dns_name
}

output "alb_zone_id" {
  description = "Application Load Balancer Zone ID"
  value       = aws_lb.cloudlens.zone_id
}

output "domain_name" {
  description = "访问域名（HTTPS）"
  value       = "https://${var.domain_name}"
}

output "route53_zone_id" {
  description = "Route 53托管区域ID"
  value       = local.route53_zone_id
}

output "route53_zone_name_servers" {
  description = "Route 53名称服务器（如果创建了新区域）"
  value       = var.create_route53_zone ? aws_route53_zone.main[0].name_servers : []
}

output "certificate_arn" {
  description = "ACM SSL证书ARN"
  value       = aws_acm_certificate_validation.cloudlens.certificate_arn
}

output "certificate_domain" {
  description = "证书域名"
  value       = var.domain_name
}

output "ssh_command" {
  description = "SSH连接命令"
  value       = "ssh -i ~/.ssh/${var.create_key_pair ? aws_key_pair.cloudlens[0].key_name : var.existing_key_name}.pem ec2-user@${aws_instance.cloudlens.public_ip}"
}

output "deployment_info" {
  description = "部署信息"
  value = {
    instance_id    = aws_instance.cloudlens.id
    public_ip      = aws_instance.cloudlens.public_ip
    domain_name    = "https://${var.domain_name}"
    alb_dns        = aws_lb.cloudlens.dns_name
    ssh_command    = "ssh -i ~/.ssh/${var.create_key_pair ? aws_key_pair.cloudlens[0].key_name : var.existing_key_name}.pem ec2-user@${aws_instance.cloudlens.public_ip}"
  }
}
