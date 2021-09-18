from commons import *
from api import *

aqlc.create_collection('chat_messages')
aqlc.create_collection('chat_channels')
aqlc.create_collection('chat_memberships')


'''
chat messages

- uid
- cid
- content
- t_c

chat_channels

- uid (creator)
- t_c
- title

chat_memberships

- uid
- cid
- t_c


'''
class Chat:
    def get_new_channel_id(self):
        return obtain_new_id('chat_channel')

    def get_channel(self, cid):
        return aql('for i in chat_channels filter i.cid==@cid return i',
            cid=cid, silent=True)[0]

    def new_membership(self, cid, uid):
        exist = aql('''for i in chat_memberships
            filter i.cid==@cid and i.uid==@uid
            return i''', cid=cid, uid=uid, silent=True)

        if exist:
            raise Exception('you are already in that channel')

        return aql('insert @k into chat_memberships', k=dict(
            uid=uid,
            cid=cid,
            t_c = time_iso_now(),
            silent=True,
        ))

    def create_channel_uid(self, uid, title):
        existing = aql('for i in chat_channels filter i.uid==@uid and i.title==@title return i', uid=uid, title=title)

        if existing:
            raise Exception('channel with the same title and owner already exists')

        cid = self.get_new_channel_id()

        newc = aql('insert @k into chat_channels return NEW',
        k=dict(
            uid=uid,
            title=title,
            cid=cid,
            t_c = time_iso_now(),
        ))[0]
        return newc

    def post_message(self, cid, uid, content):
        banned_check()

        content = content.strip()
        content_length_check(content)
        # check if channel exists
        channel = self.get_channel(cid)
        if not channel: raise Exception('channel id not found')

        # check if user in channel
        if uid>0 and channel['cid']!=1:
            if not aql('''
                for i in chat_memberships
                filter i.uid==@uid and i.cid==@cid
                return i''', uid=uid, cid=cid):

                raise Exception('you are not member of that channel')

        lastm = self.get_last_message(uid)

        cdt = 15
        earlier = time_iso_now(-cdt)

        if lastm:
            if lastm['content']==content:
                raise Exception('repeatedly sending same message')

            if lastm['t_c']>earlier:
                raise Exception(f'两次发送间隔应大于{cdt}秒，请稍微等一下')

        new_msg = dict(
            cid=cid, uid=uid, content=content, t_c=time_iso_now()
        )
        spam_detected = spam_kill(content)
        if spam_detected:
            new_msg['spam']=True

        aql('insert @k into chat_messages', k=new_msg)

        return {'error':False}


    def get_last_message(self, uid):
        lastm = aql('''
        for i in chat_messages filter i.uid==@uid sort i.t_c desc
        limit 1 return i
        ''', uid=uid)
        return None if not lastm else lastm[0]

    ############

    def create_channel(self, title):
        must_be_logged_in()
        uid = g.selfuid
        title_length_check(title)
        newc = self.create_channel_uid(uid, title)
        cid = newc['cid']
        return {'error':False,'channel':newc, 'cid':cid}

    def list_channels(self):
        uid = g.selfuid
        res = aql('for i in chat_channels return i')
        return {'channels':res}

    def join_channel(self, cid):
        must_be_logged_in()
        channel = self.get_channel(cid)
        if not channel:
            raise Exception('channel cid not found')

        uid = g.selfuid
        cuid = channel['uid']

        if uid!=cuid and channel['title']!="公海":
            # you are not owner of said channel
            followings = aql('''
            for i in followings
            filter i.follow==true
            and i.to_uid==@uid and i.uid==@cuid
            return i
            ''', uid=uid, cuid=cuid)
            if not followings:
                raise Exception('cant join channels of someone who didnt follow you')

        self.new_membership(cid, uid)

        return {'error':False}

    def post(self, cid, content):
        must_be_logged_in()
        uid = g.selfuid
        return self.post_message(cid, uid, content)

    def get_messages_after(self, cid, ts):
        ma = aqls('''
            for i in chat_messages
            filter i.cid==@cid and i.t_c > @ts
            sort i.t_c asc
            limit 25
            return i
        ''', ts=ts, cid=cid)

        for m in ma: m['content'] = self.render_message(m)
        return {'messages': ma}

    def get_messages_before(self, cid, ts):
        ma = aqls('''
            for i in chat_messages
            filter i.cid==@cid and i.t_c < @ts
            sort i.t_c desc
            limit 25
            return i
        ''', ts=ts, cid=cid)

        for m in ma: m['content'] = self.render_message(m)
        return {'messages': ma}

    def render_message(self, m):
        rendered = render_template_g('chat_message.html.jinja',
            message = m,
        )
        return rendered.strip()

    def test(self):
        return {'test':'success'}

chat = Chat()

IndexCreator.create_indices('chat_messages', [['cid','t_c'],['uid','t_c']])
IndexCreator.create_indices('chat_channels', [['cid','t_c'],['uid','t_c']])
IndexCreator.create_indices('chat_memberships',
    [['cid','uid','t_c'],['uid','t_c']])

@register('chat')
def _():
    j = g.j

    fname = j['f']
    args = j['a'] if 'a' in j else []
    kwargs = j['kw'] if 'kw' in j else {}

    f = getattr(chat, fname)
    res = f(*args, **kwargs)

    return res

@app.route('/deer')
@app.route('/liao')
@app.route('/chat')
def chatpage():
    # m = chat.get_messages_before(1, '2047')['messages']
    m = []
    return render_template_g('chat.html.jinja',
        page_title = '聊天室',
        hide_title = True,
        messages = m,
    )
