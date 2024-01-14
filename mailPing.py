import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import base64
import ast
import json

from email.message import EmailMessage
from email.mime.text import MIMEText
from email import errors


# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly", "https://www.googleapis.com/auth/gmail.send"]


def main():
  """Shows basic usage of the Gmail API.
  Lists the user's Gmail labels.
  """
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
    for message in messages:
      msg = service.users().messages().get(userId='me', id=message['id']).execute()
      headers = msg['payload']['headers']
      outputMessage = [''] * 4 #initialise array for population

      for header in headers:
        if header['name'] == 'From':
          outputMessage[0] = header['value']
        if header['name'] == 'Subject':
          outputMessage[1] = header['value']
        if header['name'] == 'Date':
          outputMessage[2] = header['value']
        if header['name'] == 'X-Mailer':
          outputMessage[3] = header['value']

      output.append(outputMessage)  
      

    with open('outputDiff.txt', 'r') as file:
        diffOutput = ast.literal_eval(file.read())

    exclusionOutput = [subarray for subarray in output if subarray not in diffOutput]
    exclusionDiffOutput = [subarray for subarray in diffOutput if subarray not in output]

    exclusion = exclusionOutput + exclusionDiffOutput
    exclusion = [x for x in exclusion if x]
    
    print(exclusion)

    if exclusion:
        sendMessage(service, 'rodd7170@gmail.com', 'rodd5901@gmail.com', 'Unchecked E-Mails', str(exclusion))

        with open('outputDiff.txt', 'w') as filehandle:
            json.dump(output, filehandle)
    else:
       print("No new E-Mail")

  except HttpError as error:
    # TODO(developer) - Handle errors from gmail API.
    print(f"An error occurred: {error}")


def sendMessage(service, messageFrom, messageTo, messageSubject, messageData):
    messageData = ast.literal_eval(messageData)

    html_content = """
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
        <h2>{}</h2>
        <table>
        <tr>
            <th>From</th>
            <th>Subject</th>
            <th>Date</th>
            <th>X-Mailer</th>
        </tr>
        {}
        </table>
    </body>
    </html>
    """.format(messageSubject, "".join("<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(messageData[index][0], messageData[index][1], messageData[index][2], messageData[index][3]) for index, value in enumerate(messageData)))

      

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



if __name__ == "__main__":
  main()