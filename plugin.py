###
# coding=UTF-8
# Copyright (c) 2013, Ashley Davis (ashley@airsi.de)
# http://kittyanarchy.net/ http://airsi.de/
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
    games. Has three commands: 'ore' for one-roll engine, 'owod' for old
    World of Darkness, and 'dh' for Dark Heresy."""
    
    ####
    ## Some utility functions
    ####
    def rollDice(self, sides, num):
        '''Rolls {num} dice of {sides} sides.'''
        #make sure we need to roll multiple dice
        if num>1:
            #initialize the list that will hold the rolled dice
            ret=[]
            #iterate without bothering to hold the iterator's current value
            for _ in repeat(None, num):
                #roll the die
                x = randint(1,sides)
                #add the die to the list
                ret+=[x]
            #sort the list from low to high, prettier
            ret.sort() # in-place
        #roll just one die
        else:
            #roll the die
            ret = [randint(1,sides),]
        return ret

    def insert(self, src, new, pos):
        '''Inserts new inside src at pos.'''
        return src[:pos] + new + src[pos:]

    def optTxt(self,num,pre="",post=""):
        '''Returns a number if it exists, with optional pre- and post- text
        formatting.'''
        txt=""
        if num:
            if pre: txt+="%s"%pre
            txt+="%s"%num
            if post: txt+="%s"%post
        return txt

    def sRep(self,arr):
        '''Returns the list or tuple as a comma delimited string.'''
        return ', '.join(str(x) for x in arr)

    ####
    ## Engine-specific functions
    ####
    #one-roll engine helper function(s)
    def matchORE(self, arr):
        '''Finds and returns the number of ORE-style matches in {arr}.'''
        #initialize our string
        ret=""
        #check matches for each number 1-10
        for x in xrange(1,11):
            #count how many times {x} is found
            y = arr.count(x)
            #if {x} is found more than once...
            if arr.count(x)>1:
                #add how many times we found {x} to our list formatted
                ret+="%sx%s, "%(y,x)
        #trim off the trailing comma
        if ret: ret=ret[0:-2]
        return ret

    #old world of darkness helper function(s)
    def matchOWOD(self,arr,diff):
        '''Finds and returns the number of times a die >= {diff} is found
        in {arr}.'''
        #initialize our counter
        y=0
        #if there's only one number, rather than a list...
        if type(arr) is int:
            #...then we just need to check if that one is a hit.
            if arr >= diff: return 1
            else: return 0
        #check each die side from our difficulty to a max of 10
        for x in xrange(diff,11):
            #if we found at least one match...
            if arr.count(x):
                #...add how many times we found that die side
                y+=arr.count(x)
        return y

    #dark heresy helper function(s)
    def matchDH(self,roll):
        '''Matches percentile rolls to their corresponding hit box, and
        returns the box that was hit.'''
        #reverse the number rolled as a string,
        #then force it back to int
        hit=int(str(roll)[::-1])
        #find where the hit landed
        if hit <= 10:
            return "Head"
        elif hit <= 20:
            return "Right Arm"
        elif hit <=30:
            return "Left Arm"
        elif hit <=70:
            return "Body"
        elif hit <=85:
            return "Right Leg"
        elif hit <=100:
            return "Left Leg"

    def nextHit(self,hit,deg):
        '''Calculates where additional hits past the second land according
        to the official hit table.'''
        #initialize our string to return
        hits=""
        #how many hits to calculate
        #degrees minus the two already determined.
        calcs=deg-2

        #hit tables
        if "Head" in hit: hitList=("Arm","Body","Arm","Body")
        elif "Arm" in hit: hitList=("Body","Head","Body","Arm")
        elif "Body" in hit: hitList=("Arm","Head","Arm","Body")
        elif "Leg" in hit: hitList=("Body","Arm","Head","Body")          

        #calculate each hit, but use indicies for our hitlists.
        #calcs will be at least 0, so need to add 1
        for x in xrange(0,calcs+1):
            #third, fourth, fifth hits as indicies.
            if x < 3: 
                hits+=", %s"%hitList[x]
            #sixth hit, no further hits
            elif x==calcs==3:
                hits+=", %s"%hitList[3]
            #sixth hit, more hits.
            else:
                #calc as fourth hit in table, index 3
                hits+=", %sx%s"%(hitList[3],calcs-2)
                #break so further hits aren't calculated.
                break
        return hits

    def isValidKind(self,kind):
        '''Checks to see if {str} is a valid attack kind.'''
        if self.isValidRanged(kind) or self.isValidMelee(kind):
            return True
        else: return False

    def isValidRanged(self,kind):
        '''Checks to see if {kind} is a valid ranged attack kind.'''
        rangedList=("auto","semi")
        return kind in rangedList

    def isValidMelee(self,kind):
        '''Checks to see if {kind} is a valid melee attack kind.'''
        meleeList=()
        return kind in meleeList        

    ####
    ## Commands
    ####

    ## Dark Heresy
    # 'dh'
    def dh(self,irc,msg,args,test,rest):
        """ <test> [<kind>] [<note>]
        -- Rolls a d100 and returns the result, and whether or not the roll
        was successful. You may optionally add a note."""
        kind=None
        ##TODO: parse {rest} to find {kind} and {note}
        if rest:
            restSplit=rest.split(' ')
            if self.isValidKind(restSplit[0]):
                kind=restSplit[0]
                note=' '.join(restSplit[1:])
            else:
                note=rest

        ##TODO: error checking will go here
        if test > 300 or test < 1:
            irc.error("You must roll a difficulty between ")
            return

        #roll against a d%
        roll=self.rollDice(100,1)[0]
        #initialize our reply string
        reply=""

        #first we check if the attack was ranged,
        #and if so whether or not the weapon jams.
        if roll >= 96 and self.isValidRanged(kind):
            reply="your weapon jams! (reroll if using unjammable weapon)"
        #check if the roll was a critfail.
        elif roll == 100:
            reply="a critical failure!"
        #finally we check if the roll was successful (roll<=test)
        elif roll <= test:
            #calculate degrees of success
            degrees=(test-roll)/10
            #add formatted success message to our reply string
            reply+="a success%s!"%self.optTxt(degrees,pre=" by ",post="°")
        #if we didn't succeed, jam, or critfail then we were unsuccessful
        else:
            #calculate degrees of success
            degrees=(roll-test)/10
            #add formatted failure message to our reply string
            reply+="unsuccessful%s."%self.optTxt(degrees,pre=" by ",post="°")
        #add the actual roll to our reply.
        reply+=" [%s]"%roll

        #check if an attack kind was specified and valid
        if kind:
            #make sure the combat hit was successful
            if "unsuccess" not in reply:
                #change reply to reflect combat mode
                reply=self.insert(reply,"ful hit",9)
                #ranged weapon firing mode
                if kind=="auto" or kind=="semi":
                    #in semi mode, need two degrees per extra hit
                    if kind=="semi": degrees=degrees/2
                    #{hits} holds our hit location string
                    #{first} holds the primary target determined by roll
                    first=hits=self.matchDH(roll)
                    #if we have any degrees, determine additional hits
                    if degrees:
                        #second hit always matches the first.
                        hits+=", %s"%hits
                        #third hit onward is determined with nextHit()
                        if degrees>1:
                            #we will pass the first hit and the number of
                            #degrees to calculate. this number will be 2+
                            hits+=self.nextHit(first,degrees)
                    #add the hits to our reply string
                    reply+=" (%s)"%hits

        #if there is a note, we will add it here
        if note: reply+=" (%s)"%note
        #send the finalized reply
        irc.reply("%s: %s"%(msg.nick,reply))
    dh = wrap(dh, ['int',
                    optional('text')
                ])

    ## Old World of Darkness
    # owod
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
                if pool > 1: times=pool
                else: times=""
                reply="Somehow, against all odds, in a true show of epic talent, you manage to succeed%s."%self.optTxt(times," "," times")
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
                reply="rolls %s"%self.sRep(rolls)
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
