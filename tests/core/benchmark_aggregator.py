# -*- coding: utf-8 -*-
"""
Performance tests for the agent/dogstatsd metrics aggregator.
"""
from aggregator import MetricsAggregator, MetricsBucketAggregator


class TestAggregatorPerf(object):

    FLUSH_COUNT = 10
    LOOPS_PER_FLUSH = 2000
    METRIC_COUNT = 5

    def test_dogstatsd_aggregation_perf(self):
        ma = MetricsBucketAggregator('my.host')

        for _ in xrange(self.FLUSH_COUNT):
            for i in xrange(self.LOOPS_PER_FLUSH):
                for j in xrange(self.METRIC_COUNT):

                    # metrics
                    ma.submit_packets('counter.%s:%s|c' % (j, i))
                    ma.submit_packets('gauge.%s:%s|g' % (j, i))
                    ma.submit_packets('histogram.%s:%s|h' % (j, i))
                    ma.submit_packets('set.%s:%s|s' % (j, 1.0))

                    # tagged metrics
                    ma.submit_packets('counter.%s:%s|c|#tag1,tag2' % (j, i))
                    ma.submit_packets('gauge.%s:%s|g|#tag1,tag2' % (j, i))
                    ma.submit_packets('histogram.%s:%s|h|#tag1,tag2' % (j, i))
                    ma.submit_packets('set.%s:%s|s|#tag1,tag2' % (j, i))

                    # sampled metrics
                    ma.submit_packets('counter.%s:%s|c|@0.5' % (j, i))
                    ma.submit_packets('gauge.%s:%s|g|@0.5' % (j, i))
                    ma.submit_packets('histogram.%s:%s|h|@0.5' % (j, i))
                    ma.submit_packets('set.%s:%s|s|@0.5' % (j, i))

            ma.flush()

    def test_checksd_aggregation_perf(self):
        ma = MetricsAggregator('my.host')

        for _ in xrange(self.FLUSH_COUNT):
            for i in xrange(self.LOOPS_PER_FLUSH):
                # Counters
                for j in xrange(self.METRIC_COUNT):
                    ma.increment('counter.%s' % j, i)
                    ma.gauge('gauge.%s' % j, i)
                    ma.histogram('histogram.%s' % j, i)
                    ma.set('set.%s' % j, float(i))
            ma.flush()

    def create_event_packet(self, title, text):
        p = "_e{{{title_len},{text_len}}}:{title}|{text}".format(
            title_len=len(title),
            text_len=len(text),
            title=title,
            text=text
        )
        return p


    def test_dogstatsd_utf8_events(self):
        ma = MetricsBucketAggregator('my.host')

        for _ in xrange(self.FLUSH_COUNT):
            for i in xrange(self.LOOPS_PER_FLUSH):
                for j in xrange(self.METRIC_COUNT):

                    ma.submit_packets(self.create_event_packet(
                        'Τη γλώσσα μου έδωσαν ελληνική',
                        """τὸ σπίτι φτωχικὸ στὶς ἀμμουδιὲς τοῦ Ὁμήρου. Μονάχη ἔγνοια ἡ γλῶσσα μου στὶς ἀμμουδιὲς τοῦ Ὁμήρου. ἀπὸ τὸ Ἄξιον ἐστί τοῦ Ὀδυσσέα Ἐλύτη"""
                    ))
                    ma.submit_packets(self.create_event_packet(
                        'ვეპხის ტყაოსანი შოთა რუსთაველი',
                        """ღმერთსი შემვედრე, ნუთუ კვლა დამხსნას სოფლისა შრომასა, ცეცხლს, წყალსა და მიწასა, ჰაერთა თანა მრომასა; მომცნეს ფრთენი და აღვფრინდე, მივჰხვდე მას ჩემსა ნდომასა, დღისით და ღამით ვჰხედვიდე მზისა ელვათა კრთომაასა.
                        """
                    ))
                    ma.submit_packets(self.create_event_packet(
                        'Traité sur la tolérance',
                        """Ose supposer qu'un Ministre éclairé & magnanime, un Prélat humain & sage, un Prince qui sait que son intérêt consiste dans le grand nombre de ses Sujets, & sa gloire dans leur bonheur, daigne jetter les yeux sur cet Ecrit informe & défectueux; il y supplée par ses propres lumieres; il se dit à lui-même: Que risquerai-je à voir la terre cultivée & ornée par plus de mains laborieuses, les tributs augmentés, l'Etat plus florissant?"""
                    ))

            ma.flush()

    def test_dogstatsd_ascii_events(self):
        ma = MetricsBucketAggregator('my.host')

        for _ in xrange(self.FLUSH_COUNT):
            for i in xrange(self.LOOPS_PER_FLUSH):
                for j in xrange(self.METRIC_COUNT):

                    ma.submit_packets(self.create_event_packet(
                        'asldkfj fdsaljfas dflksjafs fasdfkjaldsfkjasldf',
                        """alkdjfa slfalskdfjas lkfdjaoisudhfalsdkjbfaksdhfbasjdk fa;sf ljda fsafksadfh alsdjfhaskjdfgahls d;fjasdlkfh9823udjs dlfhaspdf98as ufdaksjhfaisdhufalskdjfhas df"""
                    ))
                    ma.submit_packets(self.create_event_packet(
                        'kdjfsofuousodifu982309rijdfsljsd  dfsdf sdf',
                        """dflskjdfs8d9fsdfjs sldfjka ;dlfjapfoia jsdflakjsdfp 0adsfuolwejf wflsdjf lsdkjf0saoiufja dlfjasd of;lasdjf ;askdjf asodfhas lkmfbashudf asd,fasdfna s,dfjas lcjx vjaskdlfjals dfkjasdflk jasldfkj asldkfjas ldfkasjdf a"""
                    ))
                    ma.submit_packets(self.create_event_packet(
                        'asdf askdjf asldfkjsad lfkajsdlfksajd fasdfsdfdf',
                        """skdfjsld flskdjf alksdjfpasdofuapo sdfjalksdjf ;as.kjdf ;ljLKJL :KJL:KJ l;kdsjf ;lkj :Lkj FLDKFJ LSKFDJ ;LDFJ SLKDJF KSDLjf: Lfjldkj fLKDSJf lSKDjf ls;kdjf s;lkfjs L:KAJ :LFKJDL:DKjf L:SKjf;lKDJfl;SKJDf :LKSDj;lsdfj fsdljfsd ofisunafoialjsflmsdifjas;dlkfaj sdfkasjd flaksjdfnpmsao;difjkas dfnlaksdfa;sodljfas lfdjasdflmajsdlfknaf98wouanepr9qo3ud fadspuf oaisdufpoasid fj askdjn LKJH LKJHFL KJDHSF DSFLHSL JKDFHLSK DJFHLS KJDFHS"""
                    ))

            ma.flush()

if __name__ == '__main__':
    t = TestAggregatorPerf()
    #t.test_dogstatsd_aggregation_perf()
    #t.test_checksd_aggregation_perf()
    t.test_dogstatsd_utf8_events()
