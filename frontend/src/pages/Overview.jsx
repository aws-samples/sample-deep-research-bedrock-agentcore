import React from 'react';
import {
  Container,
  Header,
  SpaceBetween,
  Box,
  Link
} from '@cloudscape-design/components';

export default function Overview() {
  return (
    <SpaceBetween size="l">
      <Container
        header={
          <Header variant="h1">
            About Deep Research Agent
          </Header>
        }
      >
        <SpaceBetween size="m">
          <Box variant="p">
            Deep Research Agent is a modular AI-powered research platform built with Amazon Bedrock AgentCore.
            It uses LangGraph workflows to conduct comprehensive, multi-dimensional research on any topic.
          </Box>
        </SpaceBetween>
      </Container>

      <Container
        header={
          <Header variant="h2">
            Architecture
          </Header>
        }
      >
        <SpaceBetween size="m">
          <Box variant="p">
            The Deep Research Agent follows a serverless, event-driven architecture leveraging Amazon Bedrock AgentCore
            for agent orchestration and AWS managed services for storage and compute.
          </Box>
          <Box textAlign="center">
            <img
              src="/docs/architecture.svg"
              alt="Deep Research Agent Architecture"
              style={{ maxWidth: '100%', height: 'auto' }}
            />
          </Box>
        </SpaceBetween>
      </Container>

      <Container
        header={
          <Header variant="h2">
            How It Works
          </Header>
        }
      >
        <SpaceBetween size="m">
          <Box variant="h3">Research Workflow</Box>
          <ol>
            <li>
              <Box variant="p">
                <strong>Topic Analysis:</strong> Identifies key dimensions and aspects to explore
              </Box>
            </li>
            <li>
              <Box variant="p">
                <strong>Research Planning:</strong> Creates structured research plans for each dimension
              </Box>
            </li>
            <li>
              <Box variant="p">
                <strong>Information Gathering:</strong> Uses multiple search tools (web, academic, news) to collect data
              </Box>
            </li>
            <li>
              <Box variant="p">
                <strong>Synthesis:</strong> Integrates findings across dimensions and generates comprehensive reports
              </Box>
            </li>
          </ol>

          <Box variant="h3">Technology Stack</Box>
          <ul>
            <li><Box variant="p"><strong>Frontend:</strong> React with CloudScape Design System</Box></li>
            <li><Box variant="p"><strong>Backend:</strong> Express.js BFF (Backend for Frontend)</Box></li>
            <li><Box variant="p"><strong>Agent Framework:</strong> LangGraph on Amazon Bedrock AgentCore</Box></li>
            <li><Box variant="p"><strong>Infrastructure:</strong> Terraform for AWS resource management</Box></li>
            <li><Box variant="p"><strong>Storage:</strong> DynamoDB for metadata, S3 for research outputs</Box></li>
          </ul>

          <Box variant="p">
            Learn more: <Link external href="https://aws.amazon.com/bedrock/agentcore/">Amazon Bedrock AgentCore Documentation</Link>
          </Box>
        </SpaceBetween>
      </Container>
    </SpaceBetween>
  );
}
