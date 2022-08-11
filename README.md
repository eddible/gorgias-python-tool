# Gorgias Python Tool

## Installation 🔍
The only requirement is `requests`

A `requirements.txt` file is provided, alternatively you can use Poetry:
* Install Poetry if you don't have it already
* Clone this repo and move into the directory (`cd gorgias-python-tool`)
* Run `poetry install`

## Configuration 🔧

Although you can pass arguments on the command line, you can use a config file to configure the most common options.
* Rename `config.ini.sample` to `config.ini`
* Open it up in your preferred text editor and modify with your details. You'll need:
  * Gorgias API Token
  * Gorgias User name
  * Gorgias Subdomain
  * The email address to send your messages from

## Examples ✏️

You can run `python main.py --help` to see a full list of arguments you can pass. Please see below for examples of how you may want to use the tool.

### Create a new ticket 

> ⭐ Just omit `--ticket-id` and your arguments will generate a new ticket. A subject for your ticket/email (`--subject`) is optional, but recommended.

`python main.py --body-html "<p>Hi Edd</p><p>How are you?</p>" --customer-email customer@company.com --subject "New ticket"`

---
### Working with existing tickets

> ⭐  For the examples below,  `--customer-email` is optional when not creating a new ticket, the original requester of the ticket will be used as the recipient.
#### Send a HTML message:

`python main.py --ticket-id 2376446 --body-html "<p>Hi Edd</p><p>How are you?</p>" --customer-email customer@company.com`

#### Send a Plain text message:

`python main.py --ticket-id 2376446 --body-text "Hi Edd, How are you?"`

#### Send as an alternative agent:

`python main.py --ticket-id 2376446 --body-text "Hi Edd, How are you?" --sender-email you@yourcompany.com`

#### Add tags to the ticket (tags that don't exist will be created - can also be done during message creation):

`python main.py --ticket-id 2376446 --tag tag1 tag2`

#### Email multiple recipients:

`python main.py --ticket-id 2376446 --body-text "Hi Edd, How are you?" --customer-email customer@company.com customer2@company.com`

#### Add an internal note to the ticket:

`python main.py --ticket-id 2376446 --body-html "<p>Hi Edd</p><p>How are you?</p>" --message-type internal-note`

#### Close an open ticket:

`python main.py --ticket-id 2376446 --close-ticket`

#### Open a closed ticket:

`python main.py --ticket-id 2376446 --open-ticket`
