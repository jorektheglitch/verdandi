"""
This module provides a wrapper for Yggdrasil admin API
"""

import asyncio
import json

import logging
from datetime import datetime as dt, timedelta as td


def human_readable(num, suffix='B'):
    for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
        if abs(num) < 1024.0:
            break
        else:
            num /= 1024.0
    else:
        unit = 'Yi'
    num = round(num, 2)
    return "{}{}{}".format(num, unit, suffix)


class YggdrasilAPI():

    def __init__(self, address='localhost', port=9001, unixsock='/var/run/yggdrasil.sock'):
        self.addr = address, port
        self.unixsock = unixsock
        self.stats = {}
        self.__init_trackers()
        asyncio.ensure_future(self.getSelf())

    async def _send_request(self, method:str, **kwargs)->dict:
        req = {'request': method, **kwargs}
        try:
            reader, writer = await asyncio.open_connection(*self.addr)
        except OSError:
            reader, writer = await asyncio.open_unix_connection(self.unixsock)
        writer.write(json.dumps(req).encode())
        response = json.loads(await reader.read())
        writer.close()
        await writer.wait_closed()
        logging.info('\n[{}] {}:{} {} request'.format(dt.now(), *self.addr, method))
        logging.debug('Response: {}'.format(response))
        if not response['status']=='success':
            raise Exception(response)
        self.stats.update(response['response'])
        return response['response']

    def _preprocess(self, **kwargs):
        if 'bytes_sent' in kwargs:
            kwargs['bytes_sent'] = human_readable(kwargs['bytes_sent'])
        if 'bytes_recvd' in kwargs:
            kwargs['bytes_recvd'] = human_readable(kwargs['bytes_recvd'])
        if 'proto' in kwargs and 'endpoint' in kwargs:
            kwargs['faddr'] = '{}://{}'.format(kwargs['proto'], kwargs['endpoint'])
        if 'uptime' in kwargs:
            sec = round(kwargs['uptime'])
            kwargs['uptime'] = str(td(seconds=sec))
        if 'last_seen' in kwargs:
            sec = round(kwargs['last_seen'])
            date = dt.now() - td(seconds=sec)
            kwargs['last_seen'] = date.strftime("%d/%m/%y %H:%M:%S")
        return kwargs

    async def getSelf(self)->dict:
        raw = await self._send_request('getSelf')
        response:dict = raw['self']
        addr, params = tuple(response.items())[0]
        return dict(addr=addr, **params)

    async def getPeers(self)->list:
        raw = await self._send_request('getPeers')
        response = raw['peers']
        return [self._preprocess(addr=addr, **params) for addr, params in response.items()]

    async def getDHT(self)->list:
        raw = await self._send_request('getDHT')
        response = raw['dht']
        return [self._preprocess(addr=addr, **params) for addr, params in response.items()]

    async def getSwitchPeers(self)->list:
        raw = await self._send_request('getSwitchPeers')
        response = raw['switchpeers']
        return [self._preprocess(id=_id, **speer) for _id, speer in response.items()]

    async def getSessions(self)->list:
        raw = await self._send_request('getSessions')
        response = raw['sessions']
        return [self._preprocess(addr=addr, **params) for addr, params in response.items()]

    async def getAllowedEncryptionPublicKeys(self)->list:
        raw = await self._send_request('getAllowedEncryptionPublicKeys')
        return raw['allowed_box_pubs']

    async def DHTping(self, box_pub_key=None, coords=None, target=None)->list:
        if target:
            nodes = await self._send_request('DHTping', box_pub_key=box_pub_key, coords=coords, target=target)
        else:
            nodes = await self._send_request('DHTping', box_pub_key=box_pub_key, coords=coords)
        return [{'addr': addr, **stats} for addr, stats in nodes['nodes'].items()]

    async def getNodeInfo(self, box_pub_key=None, coords=None):
        raw = await self._send_request('getNodeInfo', box_pub_key=box_pub_key, coords=coords)
        return raw['nodeinfo']

    def getTransitTrafic(self):
        return {
            'sent': sum(node['bytes_sent'] for node in self.stats['switchpeers'].values()),
            'recvd': sum(node['bytes_recvd'] for node in self.stats['switchpeers'].values())
        }

    def getNumOfNodes(self):
        return len(self.stats['switchpeers'])

    def add_done_callback(self, method, cb):
        self.__callbacks[method].append[cb]
        return len(self.__callbacks[method]) - 1

    def del_done_callback(self, method, cb=None):
        try:
            self.__callbacks[method].remove(cb)
        except ValueError:
            pass

    def del_done_callback_by_id(self, method, cb_id):
        try:
            del self.__callbacks[method][cb_id]
        except IndexError:
            pass

    def __init_trackers(self):
        methods = ('getAllowedEncryptionPublicKeys', 'getDHT', 'getPeers', 'getSelf', 'getSessions', 'getSwitchPeers')
        self.__callbacks = {method: [] for method in methods}
        for method_name in methods:
            wrapper = self.done_tracker()
            wrapped = wrapper(getattr(self, method_name))
            setattr(self, method_name, wrapped)

    def done_tracker(self):
        def decorator(function):
            def wrapped(*args, **kwargs):
                result = function(*args, **kwargs)
                callbacks = self.__callbacks.get(function, [])
                for callback in callbacks:
                    callback(result)
                return result
            return wrapped
        return decorator
