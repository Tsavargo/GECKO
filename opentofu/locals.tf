locals {
  source_dir  = "${path.module}/../output/source"
  package_dir = "${path.module}/../output/package"

  composite_count = length(fileset(local.source_dir, "*/config.json"))
  composites      = [for i in range(local.composite_count) : "composite-function-${i + 1}"]

  next_composite = {
    for i, name in local.composites :
    name => i + 1 < local.composite_count ? local.composites[i + 1] : null
  }
}
