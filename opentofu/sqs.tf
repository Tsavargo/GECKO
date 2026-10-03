resource "aws_sqs_queue" "composite" {
  for_each = toset(local.composites)

  name                       = "${each.key}-queue"
  visibility_timeout_seconds = 180
}
