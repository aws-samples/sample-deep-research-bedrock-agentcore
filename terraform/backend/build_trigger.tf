# =============================================================================
# Build Triggers - Separate for Research and Chat Agents
# =============================================================================

# Trigger CodeBuild for Research Agent
resource "null_resource" "build_research_agent" {
  depends_on = [
    aws_codebuild_project.research_agent_build,
    aws_s3_bucket.codebuild_artifacts,
    aws_ecr_repository.research_agent
  ]

  triggers = {
    # Rebuild when Research Agent code changes
    dockerfile_hash = filemd5("${path.module}/../../research-agent/Dockerfile")
    buildspec_hash  = filemd5("${path.module}/../../research-agent/buildspec.yml")
    requirements_hash = filemd5("${path.module}/../../research-agent/requirements.txt")
    # Hash of all source files in research-agent/src/
    src_hash = sha256(join("", [
      for f in fileset("${path.module}/../../research-agent/src", "**/*.py") :
      filesha256("${path.module}/../../research-agent/src/${f}")
    ]))
  }

  provisioner "local-exec" {
    command = <<-EOT
      set -e

      echo "📦 Packaging Research Agent source code..."
      cd ${path.module}/../..
      zip -r /tmp/research-agent-source-${random_id.suffix.hex}.zip research-agent/ shared/ \
        -x "*.git*" \
        -x "__pycache__/*" \
        -x "*.pyc"

      echo "⬆️  Uploading source to S3..."
      aws s3 cp /tmp/research-agent-source-${random_id.suffix.hex}.zip \
        s3://${aws_s3_bucket.codebuild_artifacts.bucket}/research-agent-source.zip \
        --region ${var.aws_region}

      echo "🔨 Starting CodeBuild for Research Agent..."
      BUILD_ID=$(aws codebuild start-build \
        --project-name ${aws_codebuild_project.research_agent_build.name} \
        --region ${var.aws_region} \
        --query 'build.id' \
        --output text)

      echo "Build ID: $BUILD_ID"
      echo "⏳ Waiting for build to complete..."
      echo "   (Monitor at: https://console.aws.amazon.com/codesuite/codebuild/projects/${aws_codebuild_project.research_agent_build.name}/history)"

      # Poll for build completion
      BUILD_STATUS="IN_PROGRESS"
      while [ "$BUILD_STATUS" = "IN_PROGRESS" ]; do
        sleep 10
        BUILD_STATUS=$(aws codebuild batch-get-builds \
          --ids $BUILD_ID \
          --region ${var.aws_region} \
          --query 'builds[0].buildStatus' \
          --output text)
        echo "   Build status: $BUILD_STATUS"
      done

      if [ "$BUILD_STATUS" != "SUCCEEDED" ]; then
        echo "❌ Build failed with status: $BUILD_STATUS"
        echo "Check logs: aws logs tail /aws/codebuild/${local.project_name} --follow"
        exit 1
      fi

      echo "✅ Research Agent image built and pushed successfully!"

      # Cleanup
      rm -f /tmp/research-agent-source-${random_id.suffix.hex}.zip
    EOT

    interpreter = ["/bin/bash", "-c"]
  }

  provisioner "local-exec" {
    when    = destroy
    command = "echo 'Skipping cleanup on destroy'"
  }
}

# Trigger CodeBuild for Chat Agent
resource "null_resource" "build_chat_agent" {
  depends_on = [
    aws_codebuild_project.chat_agent_build,
    aws_s3_bucket.codebuild_artifacts,
    aws_ecr_repository.chat_agent
  ]

  triggers = {
    # Rebuild when Chat Agent code changes
    dockerfile_hash = filemd5("${path.module}/../../chat-agent/Dockerfile")
    buildspec_hash  = filemd5("${path.module}/../../chat-agent/buildspec.yml")
    requirements_hash = filemd5("${path.module}/../../chat-agent/requirements.txt")
    # Hash of all source files in chat-agent/src/
    src_hash = sha256(join("", [
      for f in fileset("${path.module}/../../chat-agent/src", "**/*.py") :
      filesha256("${path.module}/../../chat-agent/src/${f}")
    ]))
  }

  provisioner "local-exec" {
    command = <<-EOT
      set -e

      echo "📦 Packaging Chat Agent source code..."
      cd ${path.module}/../..
      zip -r /tmp/chat-agent-source-${random_id.suffix.hex}.zip chat-agent/ shared/ \
        -x "*.git*" \
        -x "__pycache__/*" \
        -x "*.pyc"

      echo "⬆️  Uploading source to S3..."
      aws s3 cp /tmp/chat-agent-source-${random_id.suffix.hex}.zip \
        s3://${aws_s3_bucket.codebuild_artifacts.bucket}/chat-agent-source.zip \
        --region ${var.aws_region}

      echo "🔨 Starting CodeBuild for Chat Agent..."
      BUILD_ID=$(aws codebuild start-build \
        --project-name ${aws_codebuild_project.chat_agent_build.name} \
        --region ${var.aws_region} \
        --query 'build.id' \
        --output text)

      echo "Build ID: $BUILD_ID"
      echo "⏳ Waiting for build to complete..."
      echo "   (Monitor at: https://console.aws.amazon.com/codesuite/codebuild/projects/${aws_codebuild_project.chat_agent_build.name}/history)"

      # Poll for build completion
      BUILD_STATUS="IN_PROGRESS"
      while [ "$BUILD_STATUS" = "IN_PROGRESS" ]; do
        sleep 10
        BUILD_STATUS=$(aws codebuild batch-get-builds \
          --ids $BUILD_ID \
          --region ${var.aws_region} \
          --query 'builds[0].buildStatus' \
          --output text)
        echo "   Build status: $BUILD_STATUS"
      done

      if [ "$BUILD_STATUS" != "SUCCEEDED" ]; then
        echo "❌ Build failed with status: $BUILD_STATUS"
        echo "Check logs: aws logs tail /aws/codebuild/${local.project_name} --follow"
        exit 1
      fi

      echo "✅ Chat Agent image built and pushed successfully!"

      # Cleanup
      rm -f /tmp/chat-agent-source-${random_id.suffix.hex}.zip
    EOT

    interpreter = ["/bin/bash", "-c"]
  }

  provisioner "local-exec" {
    when    = destroy
    command = "echo 'Skipping cleanup on destroy'"
  }
}

# AgentCore Runtime dependencies
resource "null_resource" "research_agentcore_dependency" {
  depends_on = [null_resource.build_research_agent]
}

resource "null_resource" "chat_agentcore_dependency" {
  depends_on = [null_resource.build_chat_agent]
}
