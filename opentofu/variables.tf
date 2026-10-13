variable "region" {
  description = "AWS region"
  type        = string
  default     = "eu-north-1"
}

variable "scheduler" {
  description = "Scheduler used by the composite functions"
  type        = string
  default     = "persistent"

  validation {
    condition     = contains(["persistent", "oneshot", "forkjoin"], var.scheduler)
    error_message = "scheduler must be one of: persistent, oneshot, forkjoin."
  }
}
