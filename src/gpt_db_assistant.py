import os
import openai

import pyodbc, struct
import streamlit as st

class GptDbAssistant():

    def __init__(self, question):
        self.server = 'adventureworksgpt.database.windows.net'
        self.database = 'adventureWorks'
        self.username = 'user'
        self.password = 'password123!'
        self.driver= '{SQL Server}'
        self.model = "gpt-3.5-turbo"
        self.client = openai.OpenAI(api_key='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')
        self.database_info = ''
        self.question = ''
        self.question = question
        self.tries = 3

    
    def execute_query(self, text):
            
        conn_string = f'Driver={self.driver};Server=tcp:{self.server},1433;Database={self.database};Uid={self.username};Pwd={self.password};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;'
        error = 0
        message = ""
    
        with pyodbc.connect(conn_string) as conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute(text)
                    row = cursor.fetchone()
                    
                    row_list = []
                    
                    while row:
                        row_text = str(row)
                        row_list.append(row_text)
                        row = cursor.fetchone()
        
                    message = " | ".join(row_list)
                    
            except pyodbc.Error as e:
                error = 1
                message = str(e).split('[SQL Server]')[-1]
      
        return error, message


    def get_database_info(self):
        """
        GPT receives the question and the information from the database tables.
        """

        error, message = self.execute_query("""SELECT 
                    t.TABLE_SCHEMA,
                    t.TABLE_NAME,
                    STRING_AGG(c.COLUMN_NAME, ', ') AS COLUMNS
                FROM 
                    INFORMATION_SCHEMA.TABLES t
                JOIN 
                    INFORMATION_SCHEMA.COLUMNS c ON t.TABLE_SCHEMA = c.TABLE_SCHEMA AND t.TABLE_NAME = c.TABLE_NAME
                GROUP BY 
                    t.TABLE_SCHEMA, t.TABLE_NAME
                ORDER BY 
                    t.TABLE_SCHEMA, t.TABLE_NAME;
                """)
    
        self.database_info = message

        return message

    def create_query_from_question(self):

        response = self.client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": "You will be provided with business questions about data in a database and your role is to return an SQL SERVER query that can answer that question. First I will provide you with the Schema, Table name and columns of each table of the database. Each table is separated with a | : " + self.database_info
            },
            {
                "role": "user",
                "content": self.question
            }
    
        ],
        model=self.model,
        )
    
        query = response.choices[0].message.content
        one_line_query = query.replace("\n", " ")
    
        return one_line_query


    def create_query_from_question_if_error(self, query, error):
        response = self.client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": "You are an assistant that fix an SQL SERVER query, your answer must be only a query. You will receive as input the query, the error message and the question that the user wants to answer with that query. I will also provide you with the Schema, Table name and columns of each table of the database. Each table is separated with a | : " + self.database_info
            },
            {
                "role": "user",
                "content": f"The question: {self.question}. The query with an error: {query}. The error: {error}"
            }
    
        ],
        model=self.model,
        )
    
        query = response.choices[0].message.content
        one_line_query = query.replace("\n", " ")
    
        return one_line_query

    def result_answers_the_question(self, query, result):
        response = self.client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": f"You are an assistant that answers if a result of a given query can answer a question. The user will input you the result. The first word of your answer must be 'Yes' or 'No', after that you can explain the reason of your answer. Question: {self.question}. Query: {query}"
            },
            {
                "role": "user",
                "content": f"The fist row of the result is the column name. Result: {result}"
            }
    
        ],
        model=self.model,
        )
    
        message = response.choices[0].message.content
    
        return message

    def create_query_from_question_if_doesnt_answer(self,query, answer):
    
        response = self.client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": "You will be provided with business questions about data in a database and your role is to return an SQL SERVER query that can answer that question. First I will provide you with the Schema, Table name and columns of each table of the database. Each table is separated with a | : " + self.database_info
            },
            {
                "role": "user",
                "content": self.question
            },
            {
                "role": "assistant",
                "content": query
            },
            {
                "role": "user",
                "content": f"'Can this result answer my question?' Answer: '{answer}'. Please generate another query to me."
            },
    
        ],
        model=self.model,
        )
    
        query = response.choices[0].message.content
        one_line_query = query.replace("\n", " ")
    
        return one_line_query

    def final_answer(self, query, result):
        response = self.client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": f"You are an assistant that answers a user question based on a query result. The query: {query}. The query result: {result}"
            },
            {
                "role": "user",
                "content": self.question
            }
    
        ],
        model=self.model,
        )
    
        message = response.choices[0].message.content
    
        return message

    def fix_query(self, query, error, query_result, expander):
        
        if error==0:
            continue_workflow=1
            expander.write('- Query result:')
            expander.write(query_result)
        else:
            n=0
            while (error==1) and (n<self.tries):
                expander.write('- Query resulted in an error.')
                expander.write('- Error message:')
                expander.write(query_result)
                expander.write('- Generating new query...')
                query = self.create_query_from_question_if_error(query, query_result)
                error, query_result = self.execute_query(query)
                expander.write('- Query:')
                expander.write(query)
                expander.write('- Query result:')
                expander.write(query_result)

                n += 1
        
            if n==self.tries:
                continue_workflow=0
                expander.write('- Tried too many times to create a query that does not result in an error.')
            else:
                continue_workflow=1
    
        return error, query_result, continue_workflow

    def try_another_query(self, query, answer):
    
        n=0
        
        while short_answer=='No' and n<self.tries:
            query = self.create_query_from_question_if_doesnt_answer(query, answer)
            error, query_result = self.fix_query(query, error, query_result)
            
            if error==0:
                answer = self.result_answers_the_question(query, query_result)
                short_answer = answer.split(' ')[0]
                
            n+=1
    
        return answer, short_answer

    def answer_the_question(self):


        self.get_database_info()
        
        query = self.create_query_from_question()
        error, query_result = self.execute_query(query)

        expander = st.expander("Log")
        expander.write('- Query:')
        expander.write(query)
    
        error, query_result, continue_workflow = self.fix_query(query, error, query_result, expander)

        if continue_workflow==1:
            if_answers_the_question = self.result_answers_the_question(query, query_result)
            short_if_answers_the_question = if_answers_the_question.split(' ')[0]
            
            expander.write("- Query executed. But can the result answer the initial question?")
            expander.write(if_answers_the_question)

            if 'Yes' in short_if_answers_the_question:
                answer = self.final_answer(query, query_result)
                return answer
            else:
                answer, short_answer = self.try_another_query(query, answer)
                if 'Yes' in short_answer:
                    return answer
                else:
                    expander.write('- Tried too many times to create a query that answers the question.')
                    answer = "Couldn't find an answer. Please try another question."
                    return answer
                
        else:
            answer = "Couldn't find an answer. Please try another question."
            return answer
        
        

        