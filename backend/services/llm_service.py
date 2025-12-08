"""LLM service for chatbot functionality."""

import logging
import os
from abc import ABC, abstractmethod
from typing import Optional

# Try to load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv is optional

from backend.logging_config import get_logger

logger = get_logger(__name__)


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def generate_response(
        self,
        message: str,
        dataset_id: Optional[str] = None,
        conversation_history: Optional[list] = None,
    ) -> str:
        """
        Generate a response from the LLM.

        Args:
            message: User message
            dataset_id: Optional dataset ID for context
            conversation_history: Optional conversation history

        Returns:
            Generated response text
        """
        pass


class ChatGPTProvider(LLMProvider):
    """ChatGPT/OpenAI API provider."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-3.5-turbo",
        base_url: Optional[str] = None,
    ):
        """
        Initialize ChatGPT provider.

        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model: Model name (default: gpt-3.5-turbo)
            base_url: Custom base URL for API (optional, for OpenAI-compatible APIs)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL")

        if not self.api_key:
            logger.warning("OpenAI API key not provided. ChatGPT provider will not work.")

    def generate_response(
        self,
        message: str,
        dataset_id: Optional[str] = None,
        conversation_history: Optional[list] = None,
    ) -> str:
        """Generate response using ChatGPT API."""
        if not self.api_key:
            raise ValueError("OpenAI API key is required for ChatGPT provider")

        try:
            # Import openai here to avoid dependency if not using ChatGPT
            import openai

            # Configure OpenAI client
            client_kwargs = {"api_key": self.api_key}
            if self.base_url:
                client_kwargs["base_url"] = self.base_url

            client = openai.OpenAI(**client_kwargs)

            # Build messages
            messages = []
            if conversation_history:
                messages.extend(conversation_history)
            messages.append({"role": "user", "content": message})

            # Add system message if dataset_id is provided
            if dataset_id:
                system_message = {
                    "role": "system",
                    "content": f"You are helping the user analyze a dataset with ID: {dataset_id}.",
                }
                messages.insert(0, system_message)

            # Call API
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
            )

            return response.choices[0].message.content

        except ImportError:
            logger.error("openai package not installed. Install it with: pip install openai")
            raise
        except Exception as e:
            logger.exception(f"Error calling ChatGPT API: {str(e)}")
            raise


class QwenProvider(LLMProvider):
    """Qwen AI API provider."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        """
        Initialize Qwen provider.

        Args:
            api_key: Qwen API key (defaults to QWEN_API_KEY env var)
            model: Model name (defaults to QWEN_MODEL env var or "qwen-turbo")
            base_url: API base URL (defaults to QWEN_BASE_URL env var or official endpoint)
        """
        self.api_key = api_key or os.getenv("QWEN_API_KEY")
        self.model = model or os.getenv("QWEN_MODEL", "qwen-turbo")
        self.base_url = base_url or os.getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")

        if not self.api_key:
            logger.warning("Qwen API key not provided. Qwen provider will not work.")

    def generate_response(
        self,
        message: str,
        dataset_id: Optional[str] = None,
        conversation_history: Optional[list] = None,
    ) -> str:
        """Generate response using Qwen API."""
        if not self.api_key:
            raise ValueError("Qwen API key is required for Qwen provider")

        try:
            # Import openai here (Qwen uses OpenAI-compatible API)
            import openai

            # Configure OpenAI client for Qwen
            client = openai.OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )

            # Build messages
            messages = []
            if conversation_history:
                messages.extend(conversation_history)
            messages.append({"role": "user", "content": message})

            # Add system message if dataset_id is provided
            if dataset_id:
                system_message = {
                    "role": "system",
                    "content": f"You are helping the user analyze a dataset with ID: {dataset_id}.",
                }
                messages.insert(0, system_message)

            # Call API
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
            )

            return response.choices[0].message.content

        except ImportError:
            logger.error("openai package not installed. Install it with: pip install openai")
            raise
        except Exception as e:
            logger.exception(f"Error calling Qwen API: {str(e)}")
            raise


class LocalModelProvider(LLMProvider):
    """Provider for local/self-trained models."""

    def __init__(self, config: Optional[dict] = None):
        """
        Initialize Local Model provider.

        Args:
            config: Configuration dictionary for the local model
                   Expected keys:
                   - model_path: Path to the model file or directory
                   - model_type: Type of model (e.g., "transformers", "onnx", "custom")
                   - device: Device to run on ("cpu", "cuda", etc.)
        """
        self.config = config or {}
        self.model_path = self.config.get("model_path")
        self.model_type = self.config.get("model_type", "transformers")
        self.device = self.config.get("device", "cpu")
        self.model = None
        
        logger.info(f"Local Model provider initialized: type={self.model_type}, device={self.device}")
        self._load_model()

    def _load_model(self):
        """
        Load the local model.
        
        TODO: Implement model loading logic here based on model_type.
        This is a placeholder for local model integration.
        """
        if not self.model_path:
            logger.warning("No model_path provided. Local model will not be loaded.")
            return
        
        try:
            if self.model_type == "transformers":
                # Example: Load HuggingFace transformers model
                # from transformers import AutoModelForCausalLM, AutoTokenizer
                # self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
                # self.model = AutoModelForCausalLM.from_pretrained(self.model_path)
                # self.model.to(self.device)
                logger.info(f"Transformers model loading not yet implemented. Path: {self.model_path}")
            elif self.model_type == "onnx":
                # Example: Load ONNX model
                # import onnxruntime as ort
                # self.model = ort.InferenceSession(self.model_path)
                logger.info(f"ONNX model loading not yet implemented. Path: {self.model_path}")
            else:
                logger.warning(f"Unknown model type: {self.model_type}")
        except Exception as e:
            logger.exception(f"Error loading local model: {str(e)}")
            raise

    def generate_response(
        self,
        message: str,
        dataset_id: Optional[str] = None,
        conversation_history: Optional[list] = None,
    ) -> str:
        """
        Generate response using local/self-trained model.

        TODO: Implement local model inference here.
        This is a placeholder for local model integration.

        Args:
            message: User message
            dataset_id: Optional dataset ID for context
            conversation_history: Optional conversation history

        Returns:
            Generated response text
        """
        if self.model is None:
            logger.warning("Local model not loaded. Returning placeholder response.")
            return f"[Local Model Placeholder] Response to: {message}"
        
        try:
            # TODO: Implement actual model inference
            # Example for transformers:
            # inputs = self.tokenizer(message, return_tensors="pt").to(self.device)
            # outputs = self.model.generate(**inputs, max_length=512)
            # response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            # return response
            
            logger.warning("Local model inference not yet implemented. Returning placeholder response.")
            return f"[Local Model Placeholder] Response to: {message}"
        except Exception as e:
            logger.exception(f"Error generating response with local model: {str(e)}")
            raise


class LLMService:
    """Service class to manage LLM providers."""

    def __init__(
        self,
        provider: str = "qwen",
        provider_config: Optional[dict] = None,
    ):
        """
        Initialize LLM service.

        Args:
            provider: Provider name ("chatgpt", "qwen", "local", or "mock")
            provider_config: Optional configuration for the provider
        """
        self.provider_name = provider.lower()
        self.provider_config = provider_config or {}
        self.provider: Optional[LLMProvider] = None
        self._initialize_provider()

    def _initialize_provider(self):
        """Initialize the LLM provider based on configuration."""
        if self.provider_name == "chatgpt":
            self.provider = ChatGPTProvider(
                api_key=self.provider_config.get("api_key"),
                model=self.provider_config.get("model", "gpt-3.5-turbo"),
                base_url=self.provider_config.get("base_url"),
            )
        elif self.provider_name == "qwen":
            self.provider = QwenProvider(
                api_key=self.provider_config.get("api_key"),
                model=self.provider_config.get("model"),
                base_url=self.provider_config.get("base_url"),
            )
        elif self.provider_name == "local":
            self.provider = LocalModelProvider(config=self.provider_config)
        else:
            # Mock provider (fallback)
            self.provider = None
            logger.info("Using mock LLM provider (returns 'hello world')")

    def generate_response(
        self,
        message: str,
        dataset_id: Optional[str] = None,
        conversation_history: Optional[list] = None,
    ) -> str:
        """
        Generate a response using the configured LLM provider.

        Args:
            message: User message
            dataset_id: Optional dataset ID for context
            conversation_history: Optional conversation history

        Returns:
            Generated response text
        """
        if self.provider is None:
            # Mock response
            return "hello world"

        try:
            return self.provider.generate_response(
                message=message,
                dataset_id=dataset_id,
                conversation_history=conversation_history,
            )
        except Exception as e:
            logger.exception(f"Error generating LLM response: {str(e)}")
            raise


if __name__ == "__main__":
    """Usage example for LLM service."""
    import sys
    
    # Setup basic logging for example
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    
    print("=" * 60)
    print("LLM Service Usage Example")
    print("=" * 60)
    print()
    
    # Example 1: Using Qwen (default, reads from .env)
    print("Example 1: Using Qwen Provider (reads from .env)")
    print("-" * 60)
    try:
        qwen_service = LLMService(provider="qwen")
        response = qwen_service.generate_response("Hello, how are you?")
        print(f"Qwen Response: {response}")
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure QWEN_API_KEY is set in .env file or environment variables")
    print()
    
    # # Example 2: Using ChatGPT
    # print("Example 2: Using ChatGPT Provider")
    # print("-" * 60)
    # try:
    #     chatgpt_service = LLMService(
    #         provider="chatgpt",
    #         provider_config={
    #             "api_key": os.getenv("OPENAI_API_KEY"),
    #             "model": "gpt-3.5-turbo",
    #         }
    #     )
    #     response = chatgpt_service.generate_response("Hello, how are you?")
    #     print(f"ChatGPT Response: {response}")
    # except Exception as e:
    #     print(f"Error: {e}")
    #     print("Make sure OPENAI_API_KEY is set in .env file or environment variables")
    # print()
    
    # # Example 3: Using Local Model
    # print("Example 3: Using Local Model Provider (placeholder)")
    # print("-" * 60)
    # try:
    #     local_service = LLMService(
    #         provider="local",
    #         provider_config={
    #             "model_path": "/path/to/model",
    #             "model_type": "transformers",
    #             "device": "cpu",
    #         }
    #     )
    #     response = local_service.generate_response("Hello, how are you?")
    #     print(f"Local Model Response: {response}")
    # except Exception as e:
    #     print(f"Error: {e}")
    # print()
    
    # # Example 4: Using Mock (fallback)
    # print("Example 4: Using Mock Provider (fallback)")
    # print("-" * 60)
    # mock_service = LLMService(provider="mock")
    # response = mock_service.generate_response("Hello, how are you?")
    # print(f"Mock Response: {response}")
    # print()
    
    # print("=" * 60)
    # print("Usage Example Complete")
    # print("=" * 60)
    # print()
    # print("To use Qwen, create a .env file with:")
    # print("  QWEN_API_KEY=your-api-key")
    # print("  QWEN_MODEL=qwen-turbo  # optional")
    # print("  QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1  # optional")
    # print()
    # print("Or set environment variables:")
    # print("  export QWEN_API_KEY=your-api-key")
    # print("  export QWEN_MODEL=qwen-turbo")
    # print("  export QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1")
