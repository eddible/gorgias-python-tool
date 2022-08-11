import argparse
import configparser
import requests
from requests.auth import HTTPBasicAuth
import logging
import sys


class Gorgias:
    def __init__(self, subdomain=None, token=None, user_name=None):
        self.user_url = f"https://{subdomain}.gorgias.com"
        self.base_url = f"{self.user_url}/api/"
        self.auth_headers = HTTPBasicAuth(user_name, token)

    def authenticated_get(self, endpoint):
        get_request = requests.get(
            self.base_url + f"{endpoint}", auth=self.auth_headers
        )
        return get_request

    def authenticated_post(self, endpoint, data):
        post_request = requests.post(
            self.base_url + f"{endpoint}", auth=self.auth_headers, json=data
        )
        return post_request

    def authenticated_put(self, endpoint, data):
        put_request = requests.put(
            self.base_url + f"{endpoint}", auth=self.auth_headers, json=data
        )
        return put_request

    def retrieve_ticket(self, ticket_id):
        return self.authenticated_get(f"tickets/{ticket_id}")

    def list_tags(self):
        return self.authenticated_get("tags")

    def add_tag(self, new_tag):
        data = {"name": new_tag}
        return self.authenticated_post("tags", data)

    def send_message(
        self,
        ticket_id=None,
        source_to=None,
        source_from=None,
        channel="email",
        subject="",
        body_html=None,
        body_text=None,
        created_datetime=None,
        external_id=None,
        from_agent=False,
        via="api",
    ):
        if ticket_id:
            url = f"tickets/{ticket_id}/messages"  #
        if not ticket_id:
            url = f"tickets"

        # Template message body with constant values
        new_message_body = {
            "source": {"from": {"address": source_from}},
            "channel": channel,
            "from_agent": from_agent,
            "via": via,
        }

        # Add additional parameters to the body as required
        if channel == "internal-note":
            new_message_body["sender"] = {"email": source_from}
        elif channel == "email":
            new_message_body["source"]["type"] = "email"
        if source_to:
            # Different handling depending on whether there are multiple emails provided
            if type(source_to) != list:
                source_to = [source_to]
            new_message_body["source"]["to"] = []
            for email in source_to:
                new_message_body["source"]["to"].append({"address": email})

        # A lot of the keys can be added in the same way so they're looped over below.
        possible_keys = dict(
            body_text=body_text,
            body_html=body_html,
            created_datetime=created_datetime,
            external_id=external_id,
            subject=subject,
        )
        new_message_body = add_to_message(new_message_body, possible_keys)
        if not ticket_id:
            new_message_body["receiver"] = {"email": source_to[0]}
            new_message_body["sender"] = {"email": source_from}
            new_message_body["subject"] = subject
            new_message_body = {"messages": [new_message_body]}

        return self.authenticated_post(url, new_message_body)


def get_config():
    config = configparser.ConfigParser()
    config.read("config.ini")
    if "GORGIAS-AUTH" not in config:
        logging.info("No config file found, or badly formatted.")
        return {}
    config_options = ["api_token", "user_name", "subdomain", "sender_email"]
    configured_values = {}
    for option in config_options:
        configured_value = config["GORGIAS-AUTH"][f"{option}"]
        if not configured_value:
            logging.error(f"Missing {option} from config file, but it is required.")
            sys.exit()
        else:
            configured_values[option] = configured_value.strip()

    return configured_values


def add_to_message(message, keys):
    for k, v in keys.items():
        if v:
            if k not in message:
                message[k] = v
    return message


def setup_logging():
    logging.basicConfig(level=logging.DEBUG)


def check_response(response):
    if response:
        response = response.json()
    else:
        logging.error(
            f"Error connecting to Gorgias. Returned error code {response.status_code}"
        )
        sys.exit()

    return response


def tag_ticket(tags, ge, ticket_id):
    # All existing tags are downloaded first so we can check if the requested tags already exist
    all_tags = ge.list_tags()
    if "data" in all_tags.json():
        all_tags = all_tags.json()["data"]
        tag_obj = {"names": [], "ids": []}
        for t in tags:
            # Check if tag exists, if it doesn't create it.
            tag_id = [x["id"] for x in all_tags if x["name"] == t]
            if tag_id:
                tag_obj["ids"].append(tag_id[0])
                tag_obj["names"].append(t)
            else:
                new_tag = ge.add_tag(t)
                if new_tag:
                    tag_obj["names"].append(new_tag.json()["name"])
                    tag_obj["ids"].append(new_tag.json()["id"])
        url = f"tickets/{ticket_id}/tags"
        add_tags = ge.authenticated_post(url, tag_obj)
        if add_tags:
            logging.info(f"Successfully added tags to {ge.user_url}/app/ticket/{ticket_id}")


def post_to_ticket(args, ge, sender_email):
    # Compose a new message to send to the customer
    # If no email is provided, and it isn't a new ticket, email the original requester.
    customer_email = args.customer_email
    if args.ticket_id:
        if not args.customer_email:
            ticket_data = ge.retrieve_ticket(args.ticket_id)
            if ticket_data:
                ticket_data = ticket_data.json()
                customer_email = ticket_data["requester"]["email"]
    ticket_post = ge.send_message(
        ticket_id=args.ticket_id,
        source_to=customer_email,
        source_from=sender_email,
        channel=args.message_type,
        body_html=args.body_html,
        body_text=args.body_text,
        subject=args.subject,
    )

    if ticket_post:
        if args.ticket_id:
            logging.info(f"Successfully updated ticket {ge.user_url}/app/ticket/{args.ticket_id}")
        else:
            logging.info(
                f'Successfully created ticket with ID {ge.user_url}/app/ticket/{ticket_post.json()["id"]}'
            )


def arg_or_config(argument, argument_name, config):
    # If the argument is set at the CLI we'll prefer it, otherwise we'll grab it from the config file.
    # If neither offers up a value, an error is returned.
    if argument:
        return argument
    elif argument_name in config:
        if config[argument_name]:
            return config[argument_name]
    else:
        logging.error(
            f"You need to define {argument_name} in either the config file or at the CLI."
        )
        sys.exit()


def open_or_close_ticket(argument, ticket_id, status, ge):
    if argument:
        data = {"status": status}
        update_ticket = ge.authenticated_put(f"tickets/{ticket_id}/", data)
        if update_ticket:
            logging.info(f'Successfully changed the status of ticket {ge.user_url}/app/ticket/{ticket_id} to {status} ')
        sys.exit()


def main():
    # Most options can be passed as arguments. If they are in the config file, the CLI options overrides them.
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--subject",
        required=False,
        help="An optional subject if creating a new ticket",
        default=None,
    )
    parser.add_argument(
        "--ticket-id", required=False, help="The Ticket ID", default=None
    )
    parser.add_argument(
        "--api-token",
        help="Your API Token from Gorgias",
        default=None,
    )
    parser.add_argument(
        "--user-name",
        help="Your Gorgias username, most likely your email.",
        default=None,
    )
    parser.add_argument(
        "--subdomain",
        help="Your Gorgias subdomain - you don't need the full address, just the subdomain part ("
        "https://subdomain.gorgias.com/api/) ",
        default=None,
    )
    parser.add_argument(
        "--sender-email",
        help="The email address of the user who is sending the message, can be set in config.ini",
        default=None,
    )
    parser.add_argument(
        "--customer-email",
        help="Email addresses to send the message to, pass multiple emails space separated.",
        nargs="+",
        default=None,
    )
    internal_note_group = parser.add_mutually_exclusive_group(required=False)
    internal_note_group.add_argument(
        "--open-ticket",
        action="store_true",
        help="Open the ticket",
        default=None,
    )
    internal_note_group.add_argument(
        "--close-ticket",
        action="store_true",
        help="Close the ticket",
        default=None,
    )
    internal_note_group.add_argument(
        "--message-type",
        help="The type of message added to the ticket",
        default="email",
        choices=["email", "internal-note"],
    )
    body_group = parser.add_mutually_exclusive_group(required=False)
    body_group.add_argument("--body-html", help="HTML email message", default=None)
    body_group.add_argument("--body-text", help="Text email message", default=None)
    parser.add_argument(
        "--tags",
        help="Optional tags. If the tags provided do not exist, they will be created",
        nargs="+",
        default=None,
    )

    args = parser.parse_args()

    # Some additional conditions that weren't handled by argparse
    if not (args.close_ticket or args.open_ticket or args.tags) and (
        args.body_html is None and args.body_text is None
    ):
        parser.error("--body-html or --body-text is required.")

    if not args.ticket_id and not args.customer_email:
        parser.error("--customer-email is required for a new ticket.")

    # Turn on logging
    setup_logging()

    # Get the config file if present and override any provided CLI arguments.
    config = get_config()
    api_token = arg_or_config(args.api_token, "api_token", config)
    user_name = arg_or_config(args.user_name, "user_name", config)
    subdomain = arg_or_config(args.subdomain, "subdomain", config)
    sender_email = arg_or_config(args.sender_email, "sender_email", config)

    # Connect to Gorgias
    ge = Gorgias(
        subdomain=subdomain,
        token=api_token,
        user_name=user_name,
    )

    # Make a connection with the account to verify the token is okay.
    account_details = ge.authenticated_get("account")
    check_response(account_details)

    # Process open/close events if requested
    if args.close_ticket:
        open_or_close_ticket(args.close_ticket, args.ticket_id, 'closed', ge)
    elif args.open_ticket:
        open_or_close_ticket(args.open_ticket, args.ticket_id, 'open', ge)

    # Post messages to the ticket, only proceeds if an email message is provided.
    if args.body_html is not None or args.body_text is not None:
        post_to_ticket(args, ge, sender_email)

    # Tag the ticket if tags have been provided
    if args.tags:
        tag_ticket(args.tags, ge, args.ticket_id)


if __name__ == "__main__":
    main()
