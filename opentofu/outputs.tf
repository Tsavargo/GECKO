output "queue_urls" {
  description = "URL of the SQS queue of each composite"
  value       = { for name, queue in aws_sqs_queue.composite : name => queue.url }
}

output "seed_command" {
  description = "Sends the first message of the pipeline to composite-function-1's queue"
  value       = "aws sqs send-message --queue-url ${aws_sqs_queue.composite["composite-function-1"].url} --message-body '\"start\"' --message-attributes '{\"key\": {\"DataType\": \"String\", \"StringValue\": \"key-A\"}}'"
}
