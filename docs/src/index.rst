.. meta::
   :description: Official documentation for TikTokLive, the unofficial TikTok LIVE API for Python. Connect to any TikTok livestream and receive real-time comments, gifts, likes, follows and viewer counts.
   :keywords: tiktok live api, tiktok api python, tiktoklive, tiktok live chat, tiktok websocket

TikTok LIVE API for Python
==========================

This is the reference documentation for **TikTokLive**, the unofficial
Python client for the TikTok LIVE Webcast service. It connects to any public
TikTok livestream using only a creator's ``@unique_id`` and emits real-time
events for comments, gifts, likes, follows, shares, viewer counts and battles.

These docs cover the full public API surface. If you are new, start with the
quickstart in the project overview below, then move to the module reference.

What is in these docs
---------------------

- :doc:`TikTokLive` — the top-level package: client, events, protobuf schema
- :doc:`TikTokLive.client` — ``TikTokLiveClient``, connection lifecycle, configuration
- :doc:`TikTokLive.client.web` — the HTTP client and its route methods
- :doc:`TikTokLive.client.ws` — the Webcast WebSocket layer
- :doc:`TikTokLive.events` — every event type you can subscribe to
- :doc:`TikTokLive.proto` — generated protobuf message definitions

A note on production use
------------------------

TikTokLive is a reverse-engineering project, not a supported vendor API.
TikTok can and does change the Webcast protocol without notice. For workloads
that need an uptime guarantee, the managed
`TikTok LIVE WebSocket API <https://www.eulerstream.com/websockets>`_ from
`Euler Stream <https://www.eulerstream.com/>`_ handles signing, scaling and
protocol drift for you.

Module reference
----------------

.. toctree::
   :maxdepth: 3

   TikTokLive

Project overview
----------------

.. include:: ../../README.md
   :parser: myst_parser.sphinx_
