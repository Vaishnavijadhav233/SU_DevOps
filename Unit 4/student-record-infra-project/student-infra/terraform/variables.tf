variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Prefix used for naming all resources"
  type        = string
  default     = "student-platform"
}

variable "vpc_cidr" {
  type    = string
  default = "10.1.0.0/16"
}

variable "subnet_cidr" {
  type    = string
  default = "10.1.1.0/24"
}

variable "instance_type" {
  type    = string
  default = "t2.micro"
}

variable "key_name" {
  description = "Name of the EC2 key pair already imported with the AWS CLI"
  type        = string
  default     = "student-aws-key"
}

variable "app_port" {
  description = "Port the Flask container listens on"
  type        = number
  default     = 8080
}

variable "admin_cidr" {
  description = "CIDR allowed to SSH in. Use YOUR_IP/32 for real security."
  type        = string
  default     = "0.0.0.0/0"
}
