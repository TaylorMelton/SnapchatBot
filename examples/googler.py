import time, requests, tempfile, urlparse, os, boto, uuid, re
from argparse import ArgumentParser
from boto.s3.key import Key

from snapchat_agents import SnapchatAgent, Snap

def public_url_for(key):
    return ('http://%s.s3.amazonaws.com/' % key.bucket.name)  + key.key

def get_bucket(conn, name, public = False):
    b = conn.get_bucket(name)
    if public: b.make_public()
    return b

def upload_file(bucket, filename):
    print 'filename', filename
    k = Key(bucket)
    k.key = uuid.uuid4().hex + get_file_extension(filename)
    k.set_contents_from_filename(filename)
    k.make_public()
    return public_url_for(k)

def get_file_extension(filename):
    return os.path.splitext(filename)[1]

def get_url_extension(url):
    path = urlparse.urlparse(url).path
    return os.path.splitext(path)[1]

def download_file(url):
    resp = requests.get(url)
    local_file = tempfile.NamedTemporaryFile(suffix = get_url_extension(url), delete=False)
    local_file.write(resp.content)
    return local_file.name

def reverse_image_search(url):
    try:
        headers = {}
        headers['User-Agent'] = "Mozilla/5.0 (X11; Linux i686) AppleWebKit/537.17 (KHTML, like Gecko) Chrome/24.0.1312.27 Safari/537.17"
        resp = requests.get('http://www.google.com/searchbyimage?image_url=%s' % url, headers=headers)
        open("test.html", 'w').write(resp.content)
        return re.search("imgurl=([^&]*)", resp.content).group(1)
    except Exception, e:
        print e

class GooglerAgent(SnapchatAgent):
    def initialize(self, aws_key = None, aws_secret = None, bucket = None):
        self.conn = boto.connect_s3(aws_key, aws_secret)
        self.bucket = get_bucket(self.conn, bucket)

    def on_snap(self, sender, snap):
        print 'received snap'
        remote_url = upload_file(self.bucket, snap.file.name)
        print 'remote url', remote_url
        similar_url = reverse_image_search(remote_url)
        print 'similar url', similar_url
        local_filename = download_file(similar_url)
        print 'local_filename', local_filename
        snap = Snap.from_file(local_filename)
        self.send_snap([sender], snap)

    def on_friend_add(self, friend):
        self.add_friend(friend)

    def on_friend_delete(self, friend):
        self.delete_friend(friend)

if __name__ == '__main__':
    parser = ArgumentParser("Googler Agent")

    parser.add_argument('-u', '--username', required=True, type=str, help="Username of the account to run the agent on")
    parser.add_argument('-p', '--password', required=True, type=str, help="Password of the account to run the agent on")

    parser.add_argument('--aws-key', required=True, type=str, help="AWS Key")
    parser.add_argument('--aws-secret', required=True, type=str, help="AWS Secret Key")
    parser.add_argument('--bucket', required=True, type=str, help="S3 bucket")

    args = parser.parse_args()

    agent = GooglerAgent(
        args.username,
        args.password,
        aws_key = args.aws_key,
        aws_secret = args.aws_secret,
        bucket = args.bucket
    )

    agent.listen()