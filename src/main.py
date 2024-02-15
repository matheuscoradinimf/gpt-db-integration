import os
import streamlit as st
import configparser
from gpt_db_assistant import GptDbAssistant

# Function to read the config file
def read_config():
    config = configparser.ConfigParser()
    # Construct the absolute path to the config.ini file
    dir_path = os.path.dirname(os.path.realpath(__file__))
    config_path = os.path.join(dir_path, 'config.ini')
    config.read(config_path)
    return config

# Function to create an instance of GptDbAssistant
def create_assistant(question, config):
    return GptDbAssistant(server=config['database']['server'],
                          driver=config['database']['driver'],
                          database=config['database']['database'],
                          username=config['database']['username'],
                          password=config['database']['password'],
                          api_key=config['openai']['api_key'],
                          question=question)

# Function to get the answer to the user's question
def get_answer(assistant):
    status_placeholder = st.empty()
    status_placeholder.write('GPT received your question, please wait a moment...')
    answer = assistant.answer_the_question()
    status_placeholder.empty()  # Clear the placeholder
    return answer

# Main function to run the Streamlit app
def main():
    # Set up the title of the Streamlit app
    st.title('🤖 GPT <-> Azure Database 📊')

    # Create a text input for the user to input a question
    question = st.text_input("Please input your question for GPT:")

    # Check if there is a question input
    if question:
        config = read_config()
        assistant = create_assistant(question, config)
        answer = get_answer(assistant)
        
        # Display the question and answer
        st.write("**Question**: ", question)
        st.write("**Answer**:", answer)

if __name__ == "__main__":
    main()
