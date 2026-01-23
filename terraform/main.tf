provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = "CloudLens"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

# 获取当前AWS账户ID和可用区
data "aws_caller_identity" "current" {}
data "aws_availability_zones" "available" {
  state = "available"
}

# 获取最新的Amazon Linux 2023 AMI
data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]
  
  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }
  
  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# VPC和网络配置（如果不存在，创建新的）
resource "aws_vpc" "cloudlens" {
  count = var.create_vpc ? 1 : 0
  
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true
  
  tags = {
    Name = "${var.project_name}-vpc"
  }
}

# 获取默认VPC（如果使用现有VPC）
data "aws_vpc" "default" {
  count = var.create_vpc ? 0 : 1
  default = true
  
  # 如果默认VPC不存在，会报错，此时需要设置 create_vpc = true
}

# 使用创建的VPC或默认VPC
locals {
  vpc_id = var.create_vpc ? aws_vpc.cloudlens[0].id : data.aws_vpc.default[0].id
}

# 子网配置（ALB需要至少2个子网，不同可用区）
resource "aws_subnet" "cloudlens_public" {
  count = var.create_vpc ? 2 : 0
  
  vpc_id                  = local.vpc_id
  cidr_block              = count.index == 0 ? var.public_subnet_cidr : cidrsubnet(var.vpc_cidr, 8, count.index + 1)
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true
  
  tags = {
    Name = "${var.project_name}-public-subnet-${count.index + 1}"
  }
}

# 获取默认子网（如果使用现有VPC）
data "aws_subnets" "default" {
  count = var.create_vpc ? 0 : 1
  filter {
    name   = "vpc-id"
    values = [local.vpc_id]
  }
}

# 互联网网关
resource "aws_internet_gateway" "cloudlens" {
  count = var.create_vpc ? 1 : 0
  
  vpc_id = local.vpc_id
  
  tags = {
    Name = "${var.project_name}-igw"
  }
}

# 路由表
resource "aws_route_table" "cloudlens_public" {
  count = var.create_vpc ? 1 : 0
  
  vpc_id = local.vpc_id
  
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.cloudlens[0].id
  }
  
  tags = {
    Name = "${var.project_name}-public-rt"
  }
}

resource "aws_route_table_association" "cloudlens_public" {
  count = var.create_vpc ? 1 : 0
  
  subnet_id      = aws_subnet.cloudlens_public[0].id
  route_table_id = aws_route_table.cloudlens_public[0].id
}

# 安全组
resource "aws_security_group" "cloudlens_ec2" {
  name        = "${var.project_name}-ec2-sg"
  description = "Security group for CloudLens EC2 instance"
  vpc_id      = local.vpc_id
  
  # SSH访问
  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.ssh_allowed_cidrs
  }
  
  # HTTP（临时，ALB创建后可以删除）
  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  # HTTPS
  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  # 后端API（仅允许来自ALB）
  ingress {
    description     = "Backend API from ALB"
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.cloudlens_alb.id]
  }
  
  # 前端（仅允许来自ALB）
  ingress {
    description     = "Frontend from ALB"
    from_port       = 3000
    to_port         = 3000
    protocol        = "tcp"
    security_groups = [aws_security_group.cloudlens_alb.id]
  }
  
  # 出站规则
  egress {
    description = "All outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  tags = {
    Name = "${var.project_name}-ec2-sg"
  }
}

# ALB安全组
resource "aws_security_group" "cloudlens_alb" {
  name        = "${var.project_name}-alb-sg"
  description = "Security group for CloudLens ALB"
  vpc_id      = local.vpc_id
  
  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  egress {
    description = "All outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  tags = {
    Name = "${var.project_name}-alb-sg"
  }
}

# EBS卷（数据持久化）
resource "aws_ebs_volume" "cloudlens_data" {
  availability_zone = var.create_vpc ? (length(aws_subnet.cloudlens_public) > 0 ? aws_subnet.cloudlens_public[0].availability_zone : data.aws_availability_zones.available.names[0]) : data.aws_availability_zones.available.names[0]
  size              = var.ebs_volume_size
  type              = "gp3"
  encrypted         = true
  
  tags = {
    Name = "${var.project_name}-data-volume"
  }
}

# IAM角色（EC2实例使用）
resource "aws_iam_role" "cloudlens_ec2" {
  name = "${var.project_name}-ec2-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })
  
  tags = {
    Name = "${var.project_name}-ec2-role"
  }
}

# IAM策略（CloudWatch日志）
resource "aws_iam_role_policy" "cloudlens_ec2" {
  name = "${var.project_name}-ec2-policy"
  role = aws_iam_role.cloudlens_ec2.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogStreams"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "ec2:DescribeInstances",
          "ec2:DescribeTags"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "ssm:UpdateInstanceInformation",
          "ssmmessages:CreateControlChannel",
          "ssmmessages:CreateDataChannel",
          "ssmmessages:OpenControlChannel",
          "ssmmessages:OpenDataChannel"
        ]
        Resource = "*"
      }
    ]
  })
}

# IAM实例配置文件
resource "aws_iam_instance_profile" "cloudlens_ec2" {
  name = "${var.project_name}-ec2-profile"
  role = aws_iam_role.cloudlens_ec2.name
}

# EC2密钥对（如果不存在）
resource "aws_key_pair" "cloudlens" {
  count = var.create_key_pair ? 1 : 0
  
  key_name   = "${var.project_name}-key"
  public_key = var.ssh_public_key
  
  tags = {
    Name = "${var.project_name}-key"
  }
}

# EC2实例
resource "aws_instance" "cloudlens" {
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = var.instance_type
  key_name               = var.create_key_pair ? aws_key_pair.cloudlens[0].key_name : var.existing_key_name
  vpc_security_group_ids = [aws_security_group.cloudlens_ec2.id]
  iam_instance_profile   = aws_iam_instance_profile.cloudlens_ec2.name
  
  subnet_id = var.create_vpc ? aws_subnet.cloudlens_public[0].id : tolist(data.aws_subnets.default[0].ids)[0]
  
  availability_zone = var.create_vpc ? aws_subnet.cloudlens_public[0].availability_zone : null
  
  root_block_device {
    volume_type = "gp3"
    volume_size = 30  # 最小30GB（快照要求）
    encrypted   = true
  }
  
  user_data = base64encode(templatefile("${path.module}/user-data.sh", {
    domain_name     = var.domain_name
    mysql_password  = var.mysql_password
    mysql_user      = var.mysql_user
    mysql_database  = var.mysql_database
    project_name    = var.project_name
    aws_region      = var.aws_region
  }))
  
  tags = {
    Name = "${var.project_name}-instance"
  }
  
  lifecycle {
    ignore_changes = [user_data]
  }
}

# 附加EBS卷
resource "aws_volume_attachment" "cloudlens_data" {
  device_name = "/dev/sdf"
  volume_id   = aws_ebs_volume.cloudlens_data.id
  instance_id = aws_instance.cloudlens.id
}

# Route 53托管区域（如果域名在Route 53）
# 注意：如果域名不在Route 53，这个data会失败，需要设置 create_route53_zone = true 或跳过Route 53相关资源
data "aws_route53_zone" "main" {
  count = var.create_route53_zone ? 0 : 1
  name  = var.route53_zone_name
  
  # 如果找不到，会报错，此时需要设置 create_route53_zone = true 或跳过SSL证书验证
}

# 创建Route 53托管区域（如果需要）
resource "aws_route53_zone" "main" {
  count = var.create_route53_zone ? 1 : 0
  name  = var.route53_zone_name
  
  tags = {
    Name = var.route53_zone_name
  }
}

locals {
  # Route 53托管区域ID
  route53_zone_id = var.create_route53_zone ? aws_route53_zone.main[0].zone_id : (length(data.aws_route53_zone.main) > 0 ? data.aws_route53_zone.main[0].zone_id : "")
  route53_zone_name_servers = var.create_route53_zone ? aws_route53_zone.main[0].name_servers : []
}

# ACM证书（HTTPS）
resource "aws_acm_certificate" "cloudlens" {
  domain_name       = var.domain_name
  validation_method = "DNS"
  
  subject_alternative_names = [
    "*.${var.domain_name}"
  ]
  
  lifecycle {
    create_before_destroy = true
  }
  
  tags = {
    Name = "${var.project_name}-cert"
  }
}

# Route 53 DNS验证记录
resource "aws_route53_record" "cert_validation" {
  for_each = {
    for dvo in aws_acm_certificate.cloudlens.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  }
  
  allow_overwrite = true
  name            = each.value.name
  records         = [each.value.record]
  ttl             = 60
  type            = each.value.type
  zone_id         = local.route53_zone_id
}

# 证书验证
resource "aws_acm_certificate_validation" "cloudlens" {
  certificate_arn = aws_acm_certificate.cloudlens.arn
  validation_record_fqdns = [
    for record in aws_route53_record.cert_validation : record.fqdn
  ]
  
  timeouts {
    create = "5m"
  }
}

# Application Load Balancer
resource "aws_lb" "cloudlens" {
  name               = "${var.project_name}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.cloudlens_alb.id]
  # ALB需要至少2个子网（不同可用区）
  subnets            = var.create_vpc ? [
    aws_subnet.cloudlens_public[0].id,
    aws_subnet.cloudlens_public[1].id
  ] : slice(tolist(data.aws_subnets.default[0].ids), 0, min(2, length(data.aws_subnets.default[0].ids)))
  
  enable_deletion_protection = false
  enable_http2              = true
  enable_cross_zone_load_balancing = true
  
  tags = {
    Name = "${var.project_name}-alb"
  }
}

# ALB目标组（后端）
resource "aws_lb_target_group" "backend" {
  name     = "${var.project_name}-backend-tg"
  port     = 8000
  protocol = "HTTP"
  vpc_id   = local.vpc_id
  
  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
    path                = "/health"
    protocol            = "HTTP"
    matcher             = "200"
  }
  
  deregistration_delay = 30
  
  tags = {
    Name = "${var.project_name}-backend-tg"
  }
}

# ALB目标组（前端）
resource "aws_lb_target_group" "frontend" {
  name     = "${var.project_name}-frontend-tg"
  port     = 3000
  protocol = "HTTP"
  vpc_id   = local.vpc_id
  
  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
    path                = "/"
    protocol            = "HTTP"
    matcher             = "200"
  }
  
  deregistration_delay = 30
  
  tags = {
    Name = "${var.project_name}-frontend-tg"
  }
}

# 注册目标（后端）
resource "aws_lb_target_group_attachment" "backend" {
  target_group_arn = aws_lb_target_group.backend.arn
  target_id        = aws_instance.cloudlens.id
  port             = 8000
}

# 注册目标（前端）
resource "aws_lb_target_group_attachment" "frontend" {
  target_group_arn = aws_lb_target_group.frontend.arn
  target_id        = aws_instance.cloudlens.id
  port             = 3000
}

# ALB监听器（HTTP - 重定向到HTTPS）
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.cloudlens.arn
  port              = "80"
  protocol          = "HTTP"
  
  default_action {
    type = "redirect"
    
    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

# ALB监听器（HTTPS）
resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.cloudlens.arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = aws_acm_certificate_validation.cloudlens.certificate_arn
  
  # 默认路由到前端
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.frontend.arn
  }
}

# ALB监听器规则（API路由到后端 - 优先级高）
resource "aws_lb_listener_rule" "api" {
  listener_arn = aws_lb_listener.https.arn
  priority     = 100
  
  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.backend.arn
  }
  
  condition {
    path_pattern {
      values = ["/api/*"]
    }
  }
}

# Route 53 A记录（指向ALB）
# 注意：如果域名在阿里云，这个记录不会生效，需要在阿里云配置A记录指向ALB的DNS名称
resource "aws_route53_record" "cloudlens" {
  zone_id = local.route53_zone_id
  name    = var.domain_name
  type    = "A"
  
  alias {
    name                   = aws_lb.cloudlens.dns_name
    zone_id                = aws_lb.cloudlens.zone_id
    evaluate_target_health = true
  }
}

# CloudWatch日志组
resource "aws_cloudwatch_log_group" "cloudlens" {
  name              = "/aws/ec2/${var.project_name}"
  retention_in_days = 7
  
  tags = {
    Name = "${var.project_name}-logs"
  }
}

# 输出定义在 outputs.tf 文件中
