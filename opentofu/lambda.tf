data "archive_file" "composite" {
  for_each = toset(local.composites)

  type        = "zip"
  source_dir  = "${local.source_dir}/${each.key}"
  output_path = "${local.package_dir}/${each.key}.zip"
  excludes    = ["**/__pycache__/**"]
}

resource "aws_lambda_function" "composite" {
  for_each = toset(local.composites)

  function_name    = each.key
  role             = aws_iam_role.lambda.arn
  runtime          = "python3.14"
  handler          = "lambda_function.lambda_handler"
  filename         = data.archive_file.composite[each.key].output_path
  source_code_hash = data.archive_file.composite[each.key].output_base64sha256
  timeout          = 30
  memory_size      = 512

  environment {
    variables = {
      OUTPUT_QUEUE_URL = local.next_composite[each.key] == null ? "" : aws_sqs_queue.composite[local.next_composite[each.key]].url
    }
  }
}

resource "aws_lambda_event_source_mapping" "composite" {
  for_each = toset(local.composites)

  event_source_arn = aws_sqs_queue.composite[each.key].arn
  function_name    = aws_lambda_function.composite[each.key].arn
  batch_size       = 1
}
