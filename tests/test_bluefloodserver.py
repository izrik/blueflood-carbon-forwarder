import StringIO
import json
import mock
import twisted.plugins.graphite_blueflood_plugin as plugin
from twisted.test import proto_helpers


def test_service():
    service = plugin.serviceMaker.makeService(plugin.Options())
    assert isinstance(service, plugin.MultiService)

def test_factory():
    factory = plugin.GraphiteMetricFactory()
    factory.protocol = plugin.MetricLineReceiver
    factory._metric_collection = mock.MagicMock()
    proto = factory.buildProtocol(('127.0.0.1', 0))
    tr = proto_helpers.StringTransport()
    proto.makeConnection(tr)

    proto.dataReceived('foo.bar.baz 123 123456789.0\n')
    assert factory._metric_collection.collect.called_once_with('foo.bar.baz', 123456789.0, 123.0)

@mock.patch('bluefloodserver.blueflood.Agent.request')    
def test_send_blueflood(request):
    factory = plugin.GraphiteMetricFactory()
    factory.protocol = plugin.MetricLineReceiver
    plugin.MetricService(
        protocol_cls=factory.protocol,
        endpoint='',
        interval=5,
        blueflood_url='http://bluefloodurl:190',
        tenant='tenant',
        ttl=30)._setup_blueflood(factory)

    proto = factory.buildProtocol(('127.0.0.1', 0))
    tr = proto_helpers.StringTransport()
    proto.makeConnection(tr)

    proto.dataReceived('foo.bar.baz 123 123456789.0\n')
    factory.flushMetric()
    assert request.called 
    assert len(request.call_args_list) == 1
    rq = request.call_args_list[0][0]
    assert rq[0] == 'POST'
    assert rq[1] == 'http://bluefloodurl:190/v2.0/tenant/ingest'
    metrics = json.loads(rq[3]._inputFile.read())
    assert len(metrics) == 1
    assert metrics[0]['metricName'] == 'foo.bar.baz'
    assert metrics[0]['metricValue'] == 123.0
