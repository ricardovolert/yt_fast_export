/**********************************************************************
Logging entry controller for Reason

Author: Cameron Hummels <chummels@gmail.com>
Affiliation: Columbia
Author: Jeffrey S. Oishi <jsoishi@gmail.com>
Affiliation: KIPAC/SLAC/Stanford
Author: Britton Smith <brittonsmith@gmail.com>
Affiliation: MSU
Author: Matthew Turk <matthewturk@gmail.com>
Affiliation: Columbia University
Homepage: http://yt-project.org/
License:
  Copyright (C) 2011 Matthew Turk.  All Rights Reserved.

  This file is part of yt.

  yt is free software; you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation; either version 3 of the License, or
  (at your option) any later version.

  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.

  You should have received a copy of the GNU General Public License
  along with this program.  If not, see <http://www.gnu.org/licenses/>.
***********************************************************************/

Ext.define('Reason.controller.Logging', {
    extend: 'Ext.app.Controller',
    stores: [ 'LogEntries' ],
    view: ['LoggingGrid'],

    init: function() {
        this.application.addListener({
            payloadlogentry: {fn: this.addLogPayload, scope: this},
            logentry: {fn: this.addLogEntry, scope: this},
        });
    },

    addLogPayload: function(payload) {
        this.addLogEntry(payload['log_entry']);
    },

    addLogEntry: function(text) {
        this.getLogEntriesStore().add({record: text});
    },
});
