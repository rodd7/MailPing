import logging
import azure.functions as func
import os.path

import base64
import ast
import json
import re

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from email.message import EmailMessage
from email.mime.text import MIMEText
from email import errors



app = func.FunctionApp()

@app.schedule(schedule="0 0 20 * * *", arg_name="myTimer", run_on_startup=True,
              use_monitor=False) 
def timer_trigger(myTimer: func.TimerRequest) -> None:
    if myTimer.past_due:
        logging.info('The timer is past due!')

    main()

    logging.info('Python timer trigger function executed.')



# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly", "https://www.googleapis.com/auth/gmail.send"]


def main():
  profile = open('setup.json')
  profileData = json.load(profile)

  creds = None
  # The file token.json stores the user's access and refresh tokens, and is created automatically when the authorization flow completes for the first time.
  if os.path.exists("token.json"):
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
  # If there are no (valid) credentials available, let the user log in.
  if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
      creds.refresh(Request())
    else:
      flow = InstalledAppFlow.from_client_secrets_file(
          "credentials.json", SCOPES
      )
      creds = flow.run_local_server(port=0)
    # Save the credentials for the next run
    with open("token.json", "w") as token:
      token.write(creds.to_json())

  try:
    # Call the Gmail API
    service = build("gmail", "v1", credentials=creds)

    # results = service.users().labels().list(userId="me").execute()
    # labels = results.get("labels", [])

    results = service.users().messages().list(userId='me', labelIds=['UNREAD']).execute()
    messages = results.get('messages', [])

    # if not labels:
    #   print("No labels found.")
    #   return
    # print("Labels:")
    # for label in labels:
    #   print(label["name"])

    if not messages:
      print("There is no Unread E-Mail")
      return

    output = []
    unreadCount = 0
    for message in messages:
      msg = service.users().messages().get(userId='me', id=message['id']).execute()
      headers = msg['payload']['headers']
      outputMessage = [''] * 4 #initialise array for population

      for header in headers:
        if header['name'] == 'From':
          outputMessage[0] = re.sub(r'[<>]', '', header['value'])
        if header['name'] == 'Subject':
          outputMessage[1] = remove_emoji(header['value'])
        if header['name'] == 'Date':
          outputMessage[2] = header['value']
        if header['name'] == 'X-Mailer':
          outputMessage[3] = header['value']

      output.append(outputMessage)  
      unreadCount+=1

    with open('outputDiff.txt', 'r') as file:
        diffOutput = ast.literal_eval(file.read())

    exclusionOutput = [subarray for subarray in output if subarray not in diffOutput]
    exclusionDiffOutput = [subarray for subarray in diffOutput if subarray not in output]

    exclusion = exclusionOutput + exclusionDiffOutput
    exclusion = [x for x in exclusion if x]
    
    print(exclusion)

    if exclusion:
        sendMessage(service, profileData['FromEmail'], profileData['ToEmail'], profileData['Subject'], str(exclusion), unreadCount)
        profile.close()
        with open('outputDiff.txt', 'w') as filehandle:
            json.dump(output, filehandle)
            return 200
    else:
       print("No new E-Mail")

  except HttpError as error:
    # TODO(developer) - Handle errors from gmail API.
    print(f"An error occurred: {error}")

def sendMessage(service, messageFrom, messageTo, messageSubject, messageData, unreadCount):
    messageData = ast.literal_eval(messageData)

    print("this is", messageData[0][0])
    html_content = f"""
        <html>
        <head>
            <style>
            table {{
                font-family: Arial, sans-serif;
                border-collapse: collapse;
                width: 100%;
            }}

            th, td {{
                border: 1px solid #dddddd;
                text-align: left;
                padding: 8px;
            }}

            th {{
                background-color: #f2f2f2;
            }}
            </style>
        </head>

        <body>
            <h2>{messageSubject}</h2>
            <table>
            <tr>
                <th>From</th>
                <th>Subject</th>
                <th>Date</th>
                <th>X-Mailer</th>
            </tr>
            {"".join(f"<tr><td>{row[0]}</td><td>{row[1]}</td><td>{row[2]}</td><td>{row[3]}</td></tr>" for row in messageData)}
            </table>
            <p>There are in total, {str(unreadCount)} unread E-Mails on your account</p>
        </body>
        </html>
    """

    toSend = MIMEText(html_content, "html")
    toSend['to'] = messageTo
    toSend['from'] = messageFrom
    toSend['subject'] = messageSubject

    raw = base64.urlsafe_b64encode(toSend.as_bytes()).decode()
    body = {'raw' : raw}
  
    try:
        SEND = service.users().messages().send(userId='me', body=body).execute()
    except errors.MessageError as e:
        print("MessageError occured: ", e)

def remove_emoji(string):
    emoji_pattern = re.compile("["
      u"\U0001F600-\U0001F64F"  # emoticons
      u"\U0001F300-\U0001F5FF"  # symbols & pictographs
      u"\U0001F680-\U0001F6FF"  # transport & map symbols
      u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
      u"\U00002702-\U000027B0"
      u"\U000024C2-\U0001F251"
      "]+", flags=re.UNICODE)
    return emoji_pattern.sub(r'', string)

if __name__ == "__main__":
  main()