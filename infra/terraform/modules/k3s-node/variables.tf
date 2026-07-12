variable "ami_id" {
  description = "AMI ID for the k3s EC2 node"
  type        = string
}

variable "key_name" {
  description = "EC2 key pair name"
  type        = string
}

variable "k3s_version" {
  description = "k3s version string"
  type        = string
  default     = "v1.29.0+k3s1"
}

variable "cluster_name" {
  description = "Cluster name prefix for resource tags"
  type        = string
  default     = "axon"
}

variable "vpc_id" {
  description = "VPC ID — empty string means use default VPC"
  type        = string
  default     = ""
}

variable "subnet_id" {
  description = "Subnet ID — empty string means use first available subnet"
  type        = string
  default     = ""
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.large"
}
