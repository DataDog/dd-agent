# std library
import urlparse

# third party imports
import mandrill

# dd-agent imports
from checks import AgentCheck


class MandrillCheck(AgentCheck):
    """
    Mandrill agent check

    Fetches some basic stats from your Mandrill account via their api
    """
    TAG_GROUPS = ('last_30_days', 'last_60_days', 'last_7_days',
                  'last_90_days', 'today')
    TAG_STATS = ('clicks', 'complaints', 'hard_bounces', 'opens',
                 'rejects', 'reputation', 'sent', 'soft_bounces',
                 'unique_clicks', 'unique_opens', 'unsubs')

    USER_GROUPS = ('all_time', 'last_30_days', 'last_60_days',
                   'last_7_days', 'last_90_days', 'today')
    USER_STATS = ('clicks', 'complaints', 'hard_bounces', 'opens',
                  'rejects', 'sent', 'soft_bounces', 'unique_clicks',
                  'unique_opens', 'unsubs')

    URL_STATS = ('click', 'sent', 'unique_clicks')

    def parse_domain(self, url):
        """
        Helper method to grab the domain from a url
        """
        parts = urlparse.urlparse(url)
        return parts.netloc

    def check(self, instance):
        """
        Main method called for each check run
        """
        if 'api_key' not in instance:
            raise Exception('Missing "api_key" from Mandrill config')
        api_key = instance['api_key']
        client = mandrill.Mandrill(api_key)

        self.fetch_user_stats(client)
        self.fetch_url_stats(client)
        self.fetch_tag_stats(client)

    def fetch_user_stats(self, client):
        """
        Fetch and emit metrics about the current api user
        """
        info = client.users.info()
        if not info:
            return

        tags = [
            'username:%s' % (info['username'], ),
            'public_id:%s' % (info['public_id'], ),
        ]

        self.gauge('mandrill.users.backlog', info.get('backlog', 0), tags=tags)
        self.gauge('mandrill.users.hourly_quota', info.get('hourly_quota', 0), tags=tags)
        self.gauge('mandrill.users.reputation', info.get('reputation', 0), tags=tags)

        stats = info.get('stats', {})
        for group_name in self.USER_GROUPS:
            group = stats.get(group_name, {})
            for stat_name in self.USER_STATS:
                stat = group.get(stat_name, 0)
                metric = 'mandrill.users.%s.%s' % (stat_name, group_name)
                self.gauge(metric, stat, tags=tags)

    def fetch_url_stats(self, client):
        """
        Fetch and emit metrics about all urls
        """
        all_data = client.urls.list()
        if not all_data:
            return

        for url_data in all_data:
            domain = self.parse_domain(url_data.get('url', ''))
            tags = ['domain:%s' % (domain, )]
            for stat_name in self.URL_STATS:
                stat = url_data.get(stat_name, 0)
                metric = 'mandrill.urls.%s' % (stat_name, )
                # Use a histogram here since we will probably have an overlap
                # in `domain:<url-domain>` tags
                self.histogram(metric, stat, tags=tags)

    def fetch_tag_stats(self, client):
        """
        Fetch and emit metrics about all tags
        """
        tags_data = client.tags.list()
        if not tags_data:
            return

        tag_names = set(data['tag'] for data in tags_data if 'tag' in data)
        for tag_name in tag_names:
            tags = ['tag_name:%s' % (tag_name, )]

            tag_data = client.tags.info(tag=tag_name)
            tag_name = tag_data.get('tag', '')
            for stat_name in self.TAG_STATS:
                stat = tag_data.get(stat_name, 0)
                metric = 'mandrill.tags.%s.current' % (stat_name, )
                self.gauge(metric, stat, tags)

            stats = tag_data.get('stats', {})
            for group_name in self.TAG_GROUPS:
                group = stats.get(group_name, {})
                for stat_name in self.TAG_STATS:
                    stat = group.get(stat_name, 0)
                    metric = 'mandrill.tags.%s.%s' % (stat_name, group_name)
                    self.gauge(metric, stat, tags)


if __name__ == '__main__':
    import os.path

    config_file = os.path.join(os.path.dirname(__file__), '../conf.d/mandrill_check.yml')
    check, instances = MandrillCheck.from_yaml(os.path.realpath(config_file))
    for instance in instances:
        print '\nRunning the check for api_key: %s' % (instance['api_key'], )
        check.check(instance)

        print 'Events:'
        print check.get_events()
        print 'Metrics:'
        print check.get_metrics()
