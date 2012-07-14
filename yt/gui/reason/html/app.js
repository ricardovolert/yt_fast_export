/**********************************************************************
The main GUI facility for Reason

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

Ext.Loader.setConfig({enabled:true});

var reason, rdebug, examine;

Ext.application({
    requires: ['Ext.container.Viewport',
               'Reason.view.LoggingGrid',
               'Reason.view.DataObjectTree',
               'Reason.controller.widgets.SampleWidget',
               ],
    name: 'Reason',

    appFolder: 'reason/app',

    launch: function() {
        reason = this;
        this.numberOfRequests = 0;
        rdebug = this.getController("Debugger");
        this.server = this.getController("ServerCommunication");
        Ext.create('Ext.container.Viewport', {
            layout: 'border',
            items: [
                {
                    xtype: 'logginggrid',
                    autofill: true,
                    region: 'south',
                    id: "status-region",
                    cls: "status-logger",
                    split: true,
                    height: 100,
                    maxSize: 200,
                    collapsible: true,
                    title: 'Status',
                    margins: '0 0 0 0',
               }, {
                    id: 'west-panel',
                    region: 'west',
                    split: true,
                    width: 200,
                    minSize: 175,
                    maxSize: 400,
                    collapsible: true,
                    layout: {
                        type: 'vbox',
                        pack: 'start',
                        align: 'stretch',
                    },
                    items: [
                        { xtype: 'dataobjecttree', 
                          flex: 1.0},
                        { xtype: 'panel',
                          tpl: 'Pending Requests: {0}',
                          data: [0],
                          height: 30,
                          id: 'pending',
                        }
                    ],
              }, {
                xtype: 'tabpanel',
                region: 'center',
                id: 'center-panel',
                activeTab: 0,
                dockedItems: [ {
                    dock: 'top',
                    xtype: 'mainmenu',
                } ],
                items: [
                { xtype: 'panel',
                  title: 'Welcome!',
                  closeable: true,
                  autoLoad: 'help.html',
                },
                { xtype: 'ytnotebook' },
                ]
              }
            ]
        });
        this.pending = Ext.getCmp("pending");
        this.fireEvent("allowinput");
    },
    controllers : [
        'Logging',
        'DataObjects',
        'Notebook',
        'ServerCommunication',
        'WidgetDirector',
        'MenuActions',
        'Debugger',
        'FileOpen',
    ],

});
