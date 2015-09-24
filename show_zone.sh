#!/usr/bin/env bash

sl dns zone-list
sl dns zone-print 1803023
sl dns record-add 1803023 web02 A 1.1.1.1
sl dns zone-print 1803023