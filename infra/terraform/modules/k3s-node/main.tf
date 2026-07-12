data "aws_vpc" "selected" {
  id      = var.vpc_id != "" ? var.vpc_id : null
  default = var.vpc_id == "" ? true : false
}

data "aws_subnets" "selected" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.selected.id]
  }
}

# ─── Security Group ───────────────────────────────────────────────────────────
resource "aws_security_group" "k3s_node" {
  name        = "${var.cluster_name}-k3s-node"
  description = "Security group for ${var.cluster_name} k3s node"
  vpc_id      = data.aws_vpc.selected.id

  # k3s API server
  ingress {
    description = "k3s API server"
    from_port   = 6443
    to_port     = 6443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # SSH
  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # NodePort range
  ingress {
    description = "NodePort services"
    from_port   = 30000
    to_port     = 32767
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Flannel VXLAN
  ingress {
    description = "Flannel VXLAN"
    from_port   = 8472
    to_port     = 8472
    protocol    = "udp"
    self        = true
  }

  # kubelet health check
  ingress {
    description = "kubelet"
    from_port   = 10250
    to_port     = 10250
    protocol    = "tcp"
    self        = true
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name    = "${var.cluster_name}-k3s-node"
    Project = var.cluster_name
  }
}

# ─── EC2 Instance ────────────────────────────────────────────────────────────
resource "aws_instance" "k3s_node" {
  ami                    = var.ami_id
  instance_type          = "t3.large" # 2 vCPU, 8GB — sufficient for full local stack
  key_name               = var.key_name
  subnet_id              = var.subnet_id != "" ? var.subnet_id : data.aws_subnets.selected.ids[0]
  vpc_security_group_ids = [aws_security_group.k3s_node.id]

  root_block_device {
    volume_type           = "gp3"
    volume_size           = 50
    delete_on_termination = true
    encrypted             = true
  }

  user_data = templatefile("${path.module}/userdata.sh", {
    k3s_version  = var.k3s_version
    cluster_name = var.cluster_name
  })

  tags = {
    Name        = "${var.cluster_name}-k3s-node"
    Project     = var.cluster_name
    ManagedBy   = "terraform"
  }
}

# ─── Elastic IP ───────────────────────────────────────────────────────────────
resource "aws_eip" "k3s_node" {
  instance = aws_instance.k3s_node.id
  domain   = "vpc"

  tags = {
    Name    = "${var.cluster_name}-k3s-eip"
    Project = var.cluster_name
  }
}
