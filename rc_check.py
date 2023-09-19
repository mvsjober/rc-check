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
verbose = False


def print_item(s):
    t = s['t']
    if t == 'd':
        l = '@'
    else:
        l = '#'
        
    cnt = ''
    if 'tunread' in s and len(s['tunread']) > 0:
        cnt += "[thread replies:{}]".format(len(s['tunread']))

    if 'unread' in s and s['unread'] > 0:
        cnt += "[unread:{}]".format(s['unread'])

    if 'userMentions' in s and s['userMentions'] > 0:
        cnt += "[user mentions:{}]".format(s['userMentions'])
        
    if 'groupMentions' in s and s['groupMentions'] > 0:
        cnt += "[group mentions:{}]".format(s['groupMentions'])
        
    name = s['name']
    if 'fname' in s:
        name = s['fname']
    if 'f' in s and s['f']:
        name += " ★"

    print(l + name, cnt)
    if verbose:
        pprint(s)


def print_msg(m, pre=None, post='', clip=None):
    if pre is None:
        pre = '-- ' if 'tmid' in m else '- '

    msg = m['msg']
    if len(msg) == 0 and 'attachments' in m:
        msg = m['attachments'][0]['description'] + ' <' + serverurl + m['attachments'][0]['image_url'] + '>'

    if clip is not None:
        msg = msg[:clip].replace('\n', ' ') + "..."
    print(pre + "[" + m['u']['username'] + "]: "+ msg + post)
    if verbose:
        pprint(m)
    

def main(args):
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
                t = s['t']  # type: channel (c) or private group (p)
                            # or direct message (d)
                if t == 'c' or t == 'p':
                    # Unless --all flag is set, show only favourite
                    # channels
                    if args.all:
                        show = True
                    else:
                        show = s.get('f', False)

                    # always show thread replies
                    if 'tunread' in s and len(s['tunread']) > 0:
                        show = True
                    
                    if show:
                        chanmsgs.append(s)
                    
                elif t == 'd':
                    privmsgs.append(s)
                else:
                    print('WARNING: unknown subscription type: ' + t)
                        
        if len(privmsgs) > 0:
            for s in privmsgs:
                print_item(s)
                timestamp = s['ls']
                h = rocket.im_history(room_id=s['rid'],
                                        oldest=timestamp).json()
                if h is not None and h['success']:
                    for m in reversed(h['messages']):
                        print_msg(m)

                print()

        if len(chanmsgs) > 0:
            prev_tmid = None
            for s in chanmsgs:
                print_item(s)
                timestamp = s['ls']
                tunread = s.get('tunread', [])
                fav = s.get('f', False)
                
                h = None
                if s['t'] == 'p':
                    h = rocket.groups_history(room_id=s['rid'],
                                              oldest=timestamp).json()
                elif s['t'] == 'c':
                    h = rocket.channels_history(room_id=s['rid'],
                                                oldest=timestamp).json()

                if h is not None and h['success']:
                    msgs = h['messages']
                    for m in reversed(msgs):
                        if 'tmid' not in m:
                            if fav or args.all:
                                print_msg(m)
                                prev_tmid = m['_id']
                        else:
                            is_tunread = m['tmid'] in tunread
                            if args.all or is_tunread:
                                if prev_tmid is None or prev_tmid != m['tmid']:
                                    p = rocket.chat_get_message(msg_id=m['tmid']).json()['message']
                                    print_msg(p, pre='(', post=')', clip=50)
                                print_msg(m)
                                prev_tmid = None

                print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('-a', '--all', action='store_true',
                        help='Show all channels with new posts, '
                        'not just threads and favorites')

    args = parser.parse_args()
    verbose = args.verbose
    
    main(args)
