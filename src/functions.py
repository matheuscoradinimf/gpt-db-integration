import os
import openai

import pyodbc, struct

def execute_query(text, conn_string):

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


def get_database_info(conn_string):

    error, message = execute_query("""SELECT 
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
            """, conn_string)

    return message


def create_query_from_question(question, database_info):
    response = client.chat.completions.create(
    messages=[
        {
            "role": "system",
            "content": "You will be provided with business questions about data in a database and your role is to return an SQL SERVER query that can answer that question. First I will provide you with the Schema, Table name and columns of each table of the database. Each table is separated with a | : " + database_info
        },
        {
            "role": "user",
            "content": question
        }

    ],
    model=model,
    )

    query = response.choices[0].message.content
    one_line_query = query.replace("\n", " ")

    return one_line_query


def create_query_from_question_if_error(question, query, error, database_info):
    response = client.chat.completions.create(
    messages=[
        {
            "role": "system",
            "content": "You are an assistant that fix an SQL SERVER query, your answer must be only a query. You will receive as input the query, the error message and the question that the user wants to answer with that query. I will also provide you with the Schema, Table name and columns of each table of the database. Each table is separated with a | : " + database_info
        },
        {
            "role": "user",
            "content": f"The question: {question}. The query with an error: {query}. The error: {error}"
        }

    ],
    model=model,
    )

    query = response.choices[0].message.content
    one_line_query = query.replace("\n", " ")

    return one_line_query

def result_answers_the_question(question, query, result):
    response = client.chat.completions.create(
    messages=[
        {
            "role": "system",
            "content": f"You are an assistant that answers if a result of a given query can answer a question. The user will input you the result. The first word of your answer must be 'Yes' or 'No', after that you can explain the reason of your answer. Question: {question}. Query: {query}"
        },
        {
            "role": "user",
            "content": f"The fist row of the result is the column name. Result: {result}"
        }

    ],
    model=model,
    )

    message = response.choices[0].message.content

    return message

def create_query_from_question_if_doesnt_answer(question, query, answer, database_info):

    response = client.chat.completions.create(
    messages=[
        {
            "role": "system",
            "content": "You will be provided with business questions about data in a database and your role is to return an SQL SERVER query that can answer that question. First I will provide you with the Schema, Table name and columns of each table of the database. Each table is separated with a | : " + database_info
        },
        {
            "role": "user",
            "content": question
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
    model=model,
    )

    query = response.choices[0].message.content
    one_line_query = query.replace("\n", " ")

    return one_line_query

def final_answer(question, query, result):
    response = client.chat.completions.create(
    messages=[
        {
            "role": "system",
            "content": f"You are an assistant that answers a user question based on a query result. The query: {query}. The query result: {result}"
        },
        {
            "role": "user",
            "content": question
        }

    ],
    model=model,
    )

    message = response.choices[0].message.content

    return message

def fix_query(question, query, error, query_result, database_info, conn_string):

    continue_workflow=1
    
    if error==0:
        print("Query executed. But can the result answer the initial question? \n")
    else:
        n=0
        while (error==1) and (n<3):
            print('Query resulted in an error. \n')
            print(f'Error message: {query_result}')
            query = create_query_from_question_if_error(question, query, query_result, database_info)
            print(f'Query: \n {query} \n')
            error, query_result = execute_query(query, conn_string)
            n += 1
    
        if n==3:
            print("Tried to execute a valid query 3x but with no success.")
            continue_workflow=0

    return error, query_result


def try_another_query(question, query, answer, database_info, conn_string):

    n=0
    while short_answer=='No' and n<3:
        query = create_query_from_question_if_doesnt_answer(question, query, answer, database_info)
        error, query_result = fix_query(question, query, error, query_result, database_info, conn_string)
        
        if error==0:
            answer = result_answers_the_question(question, query, query_result)
            short_answer = answer.split(' ')[0]
            print(answer + '\n')
            
        n+=1

    return answer, short_answer


def answer_the_question(question, database_info, conn_string):
    query = create_query_from_question(question, database_info)
    print(f'Query: \n {query} \n')
    error, query_result = execute_query(query, conn_string)

    error, query_result = fix_query(question, query, error, query_result, database_info, conn_string)

    if error==0:
        if_answers_the_question = result_answers_the_question(question, query, query_result)
        short_if_answers_the_question = if_answers_the_question.split(' ')[0]
        print(if_answers_the_question + '\n')

        if 'Yes' in short_if_answers_the_question:
            answer = final_answer(question, query, query_result)
            print(answer)
        else:
            answer, short_answer = try_another_query(question, query, answer, database_info)
            if 'Yes' in short_answer:
                print(answer)
            else:
                print("Couldn't find an answer to the question.")