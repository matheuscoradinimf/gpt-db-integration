import os
import openai

import pyodbc, struct
import streamlit as st

from gpt_db_assistant import GptDbAssistant


# Set up the title of the Streamlit app
st.title('🤖 GPT <-> AdventureWorks 📊')

# Create a text input for the user to input a question
question = st.text_input("Please input your question for GPT:")

# Check if there is a question input
if question and len(question)>=1:
    # Instance the GptDbAssistant with the question
    assistant = GptDbAssistant(question)
    
    # Create an empty placeholder
    status_placeholder = st.empty()
    status_placeholder.write('GPT received your question, please wait a moment...')

    # Get the answer to the question
    answer = assistant.answer_the_question()

    # Update the placeholder with the answer
    status_placeholder.write('')  # Clear the placeholder
    
    # Display the question and answer
    st.write("**Question**: ", question)
    st.write("**Answer**:", answer)