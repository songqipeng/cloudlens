variable "aws_region" {
  description = "AWS区域"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "项目名称"
  type        = string
  default     = "cloudlens"
}

variable "environment" {
  description = "环境名称"
  type        = string
  default     = "production"
}

variable "domain_name" {
  description = "域名（例如: cloudlens.songqipeng.com）"
  type        = string
  default     = "cloudlens.songqipeng.com"
}

variable "route53_zone_name" {
  description = "Route 53托管区域名称（例如: songqipeng.com）"
  type        = string
  default     = "songqipeng.com"
}

variable "create_route53_zone" {
  description = "是否创建新的Route 53托管区域（如果域名已在Route 53，设为false）"
  type        = bool
  default     = false
}

variable "instance_type" {
  description = "EC2实例类型"
  type        = string
  default     = "t3.medium"
  
  validation {
    condition = contains([
      "t3.small", "t3.medium", "t3.large",
      "t3a.small", "t3a.medium", "t3a.large"
    ], var.instance_type)
    error_message = "实例类型必须是t3或t3a系列（small/medium/large）"
  }
}

variable "ebs_volume_size" {
  description = "EBS数据卷大小（GB）"
  type        = number
  default     = 50
}

variable "create_vpc" {
  description = "是否创建新的VPC（如果使用现有VPC，设为false）"
  type        = bool
  default     = false
}

variable "vpc_cidr" {
  description = "VPC CIDR块（仅在create_vpc=true时使用）"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidr" {
  description = "公有子网CIDR块（仅在create_vpc=true时使用）"
  type        = string
  default     = "10.0.1.0/24"
}

variable "ssh_allowed_cidrs" {
  description = "允许SSH访问的CIDR列表"
  type        = list(string)
  default     = ["0.0.0.0/0"]  # 生产环境应该限制为特定IP
}

variable "create_key_pair" {
  description = "是否创建新的EC2密钥对"
  type        = bool
  default     = true
}

variable "existing_key_name" {
  description = "现有EC2密钥对名称（仅在create_key_pair=false时使用）"
  type        = string
  default     = ""
}

variable "ssh_public_key" {
  description = "SSH公钥（仅在create_key_pair=true时使用）"
  type        = string
  default     = ""
}

variable "mysql_user" {
  description = "MySQL用户名"
  type        = string
  default     = "cloudlens"
  sensitive   = true
}

variable "mysql_password" {
  description = "MySQL密码（建议使用随机生成）"
  type        = string
  sensitive   = true
}

variable "mysql_database" {
  description = "MySQL数据库名"
  type        = string
  default     = "cloudlens"
}
