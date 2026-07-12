output "node_ip" {
  description = "Public (Elastic) IP of the k3s node"
  value       = aws_eip.k3s_node.public_ip
}

output "private_ip" {
  description = "Private IP of the k3s node"
  value       = aws_instance.k3s_node.private_ip
}

output "instance_id" {
  description = "EC2 instance ID"
  value       = aws_instance.k3s_node.id
}

output "security_group_id" {
  description = "Security group ID attached to the k3s node"
  value       = aws_security_group.k3s_node.id
}
