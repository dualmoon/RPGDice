###
# coding=UTF-8
# Copyright (c) 2012, Ashley Davis
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from random import randint
from itertools import repeat
import re,string

class RPGDice(callbacks.Plugin):
    """A plugin that rolls various dice sets for pen-and-pad roleplaying 
    games. Has two commands: 'ore,' and 'owod'"""
    
    # Some utility functions
    def rollDice(self, sides, num):
        if num>1:
            ret=[]
            for _ in repeat(None, num):
                x = randint(1,sides+1)
                ret+=[x]
            ret.sort() # in-place
        else:
            ret = randint(1,sides+1)
        return ret
    
    def matchORE(self, arr):
        str=""
        for x in xrange(1,11):
            y = arr.count(x)
            if y>1:
                str+="%sx%s, "%(y,x)
        if str: str=str[0:-2]
        return str

    def matchOWOD(self,arr,diff):
        y=0
        for x in xrange(diff,11):
            if arr.count(x):
                y+=arr.count(x)
        return y

    def optTxt(self,num,pre="",post=""):
        txt=""
        if num:
            if pre: txt+="%s"%pre
            txt+="%s"%num
            if post: txt+="%s"%post
        return txt

    def dh(self,irc,msg,args,mod,kind,note):
        """ <modifier> [<kind>] [<note>] --
        -- Rolls a d100 and returns the result, and whether or not the roll
        was successful."""
        ##TODO: error checking will go here
        if mod > 1000 or mod < 1:
            irc.error("Is that really necessary?")
            return

        #roll and define success or fail.
        roll=self.rollDice(100,1)
        reply=""
        if roll <= mod:
            degrees=(mod-roll)/10
            reply+="a successful hit%s!"%self.optTxt(degrees,pre=" by ",post="°")
        else:
            degrees=(roll-mod)/10
            reply+="a miss%s"%self.optTxt(degrees,pre=" by ",post="°")
        reply+=" [%s]"%roll

        if kind:
            reply+=" {DEBUG: kind: %s}"%kind

        #final reply
        irc.reply("%s: %s"%(msg.nick,reply))
    dh = wrap(dh, ['int',
                    optional('somethingWithoutSpaces'),
                    optional('text')
                ])

    def owod(self,irc,msg,args,pool,diff,note):
        """ <number of dice> [<difficulty=6>] [<note>] 
        -- Rolls d10's and returns the results, and whether or not the roll
         was successful. Can add a note optionally after your dice."""
        ##(user) rolls (rolls) to (note). (N successes|failure|botch!)
        ##Luna rolls 1,2,3,4,7,8 to summon evil things. (2 successes)
        ##Luna rolls 1,3,3 to pick the lock. (botch!)

        #start with error checking.
        if pool > 20 or pool < 1:
            irc.error("You must roll between 1 and 20 dice.")
        else:
            if diff == 1:
                if pool > 1: times=" %s times"%pool
                reply="Somehow, against all odds, in a true show of epic talent, you manage to succeed%s."%times
                action=False
            elif diff > 10:
                reply="You fail. Probably because you're too stupid to even know how many sides a d10 has."
                action=False
            else:
                #error checking complete, time to make the roll.
                rolls = self.rollDice(10,pool)
                if not diff: diff=6
                match = self.matchOWOD(rolls,diff)
                if match == 1:
                    result="1 success"
                elif match > 1:
                    result="%s successes"%match
                elif not match and 1 in rolls:
                    result="botch!"
                else:
                    result="failure"
                reply="rolls %s"%str(rolls)[1:-1]
                if note:
                    reply+=" to %s."%note
                reply+=" (%s)"%result
                action=True
            irc.reply(reply, action=action)
    owod = wrap(owod, ['int',
                        optional('int'),
                        optional('text')
                    ])

    def ore(self,irc,msg,args,num,call,expert,text):
        """ <number of dice> [<called>] [<expert>] [<note>]  
        --  Rolls d10's and returns the results, including any pairs. 
        Can add a note optionally after your dice. """
        if (num > 10) or (num < 1):
            irc.error("You must roll between 1 and 10 dice.")
        else:
            if not text: text=""
            arr=self.rollDice(10,num)
            ##parse text for calls and/or expert dice.
            #first look for exactly one call
            if text and call: text+=", "
            if call:
                if 10 < call > 1:
                    irc.error("They're d10s, you idiot. You can't call a side that doesn't exist.")
                    return
                else:
                    arr+=[call]
                    text+="called:%s"%call
            if text and expert: text+=", "
            if expert: arr+=[expert];text+="expert:%s"%expert
            match=self.matchORE(arr)
            reply="%s: %s"%(match,str(arr))
            if text:
                reply+=" (%s)"%text
            irc.reply(reply)
    ore = wrap(ore, ['int',
                     optional('int'),
                     optional('int'),
                     optional('text')
                    ])

Class = RPGDice


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
