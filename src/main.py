import os
import openai

import pyodbc, struct
import streamlit as st

from gpt_db_assistant import GptDbAssistant


# Set up the title of the Streamlit app
st.title('GPT <-> AdventureWorks')

# Create a text input for the user to input a question
question = st.text_input("Please input your question for GPT:")

# Check if there is a question input
if question:
    # Instance the GptDbAssistant with the question
    assistant = GptDbAssistant(question)
    
    # Get the answer to the question
    answer = assistant.answer_the_question()
    
    # Display the answer
    st.write("Answer:", answer)