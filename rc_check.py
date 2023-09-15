#!/usr/bin/python3

import argparse
import os
import sys
from datetime import datetime, timezone
from requests import sessions
from pprint import pprint
from rocketchat_API.rocketchat import RocketChat

serverurl = os.environ.get('RC_SERVER')
username = os.environ.get('RC_USERNAME')
password = os.environ.get('RC_PASSWORD')


def print_item(s, verbose):
    cnt = ' '
    if 'tunread' in s and len(s['tunread']) > 0:
        cnt = len(s['tunread'])

    if 'unread' in s and s['unread'] > 0:
        cnt = f"[{s['unread']}]"

    name = s['name']
    if 'fname' in s:
        name = s['fname']

    print(cnt, name)
    if verbose:
        pprint(s)


def print_history(h, verbose):
    global serverurl
    
    if h is not None and h['success']:
        msgs = h['messages']
        for m in reversed(msgs):
            pre = ''
            if 'tmid' in m:
                pre = '- '
            msg = m['msg']
            if len(msg) == 0 and 'attachments' in m:
                msg = m['attachments'][0]['description'] + ' <' + serverurl + m['attachments'][0]['image_url'] + '>'
            print(pre + "[" + m['u']['username'] + "]: "+ msg)
            if verbose:
                pprint(m)


def main(args):
    timestamp = None  # should read this from file
    # timenow = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")

    if username is None or password is None:
        print('ERROR: server URL, username and password must be set with '
              'RC_SERVER, RC_USERNAME and RC_PASSWORD environment variables.')
        sys.exit(1)

    with sessions.Session() as session:
        rocket = RocketChat(username, password, server_url=serverurl,
                            session=session)
        subs = rocket.subscriptions_get().json()
        if not subs['success']:
            print('ERROR: unable to fetch subscriptions for RocketChat server.')
            sys.exit(1)

        chanmsgs = []
        privmsgs = []

        for s in subs['update']:
            if s['alert']:
                t = s['t']  # type, e.g. channel or privmsg
                if t == 'c' or t == 'p':
                    show = args.all
                    
                    if 'f' in s and s['f']:  # favorites always shown
                        show = True

                    # always show thread replies
                    if 'tunread' in s and len(s['tunread']) > 0:
                        show = True
                    
                    if show:
                        chanmsgs.append(s)
                    
                elif t == 'd':
                    privmsgs.append(s)
                else:
                    print('WARNING: unknown subscription type: ' + t)
                    if args.verbose:
                        pprint(s)

        if len(privmsgs) > 0:
            print('Private messages')
            for s in privmsgs:
                print_item(s, args.verbose)
                his = rocket.im_history(room_id=s['rid'], count=4, oldest=timestamp).json()
                print_history(his, args.verbose)

        if len(chanmsgs) > 0:
            print('Channels and discussions:')
            for s in chanmsgs:
                print_item(s, args.verbose)
                his = None
                if s['t'] == 'p':
                    his = rocket.groups_history(room_id=s['rid'], count=4, oldest=timestamp).json()
                elif s['t'] == 'c':
                    his = rocket.channels_history(room_id=s['rid'], count=4, oldest=timestamp).json()
                print_history(his, args.verbose)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('-a', '--all', action='store_true',
                        help='Show all channels with new posts, '
                        'not just threads and favorites')

    args = parser.parse_args()
    main(args)
