from src.core.ports.llm_provider_port import LLMProviderPort
import os
import boto3
from langchain_aws import ChatBedrockConverse

class AWSBedrockProviderAdapter(LLMProviderPort):
  def __init__(self):
    self.aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
    self.aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    self.aws_region = os.getenv("AWS_REGION", "us-east-1")

  def get_llm(self, llm_id: str):
    aws_session = boto3.Session(
        aws_access_key_id=self.aws_access_key,
        aws_secret_access_key=self.aws_secret_key,
        region_name=self.aws_region)

    bedrock_client = aws_session.client("bedrock-runtime")
    llm = ChatBedrockConverse(
      client=bedrock_client,
      model_id=llm_id
    )
    return llm