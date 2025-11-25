import os
from dotenv import load_dotenv
from azure_auth import setup_azure_openai_client
from local_openai import setup_local_openai_client

# Load environment variables
load_dotenv()

def main():
    # Determine which client to use based on USE_AZURE environment variable
    use_azure = os.getenv("USE_AZURE", "false").lower() == "true"

    if use_azure:
        client = setup_azure_openai_client()
        model = os.environ["AZURE_OPENAI_MODEL"]
        mode = "Azure OpenAI"
    else:
        client = setup_local_openai_client()
        model = os.environ["OPENAI_MODEL"]
        mode = "OpenAI"

    messages = []

    print(f"{mode} Chat Assistant. Type 'exit' to quit.")

    while True:
        user_input = input("\nYou: ")
        if user_input.lower() == "exit":
            break

        # Add user message to conversation history
        messages.append({"role": "user", "content": user_input})

        # Call OpenAI (Azure or standard)
        response = client.chat.completions.create(
            model=model,
            messages=messages
        )

        # Get the assistant's response
        assistant_response = response.choices[0].message.content

        # Add assistant response to conversation history
        messages.append({"role": "assistant", "content": assistant_response})

        # Display the response
        print("\nAssistant:", assistant_response)

if __name__ == '__main__':
    main()