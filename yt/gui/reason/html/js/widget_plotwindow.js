/**********************************************************************
The Plot Window Widget

Author: Cameron Hummels <chummels@gmail.com>
Affiliation: Columbia
Author: Jeffrey S. Oishi <jsoishi@gmail.com>
Affiliation: KIPAC/SLAC/Stanford
Author: Britton Smith <brittonsmith@gmail.com>
Affiliation: MSU
Author: Matthew Turk <matthewturk@gmail.com>
Affiliation: NSF / Columbia
Homepage: http://yt.enzotools.org/
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



var WidgetPlotWindow = function(python_varname) {
    this.id = python_varname;
    this.print_python = function(b, e) {
        yt_rpc.ExtDirectREPL.execute(
            {code:'print "' + python_varname + '"'},
            function(f, a) {alert(a.result['output']);}
        );
    }

    viewport.get("center-panel").add(
        {
            xtype: 'panel',
            id: "pw_" + this.id,
            title: "Plot Window",
            iconCls: 'graph',
            autoScroll: true,
            layout:'absolute',
            closable: true,
            items: [ 
                {
                    xtype:'panel',
                    id: 'image_panel_' + this.id,
                    autoEl: {
                        tag: 'img',
                        id: "img_" + this.id,
                        width: 400,
                        height: 400,
                    },
                    x: 100,
                    y: 10,
                    width: 400,
                    height: 400,
                }, {
                    xtype:'button',
                    text: 'North',
                    x: 30,
                    y: 10,
                    handler: function(b,e) {
                        cc = python_varname + '.pan_rel((0.0, -0.5))'
                        yt_rpc.ExtDirectREPL.execute(
                        {code:cc}, handle_payload); 
                    }
                }, {
                    xtype:'button',
                    text:'East',
                    x : 50,
                    y : 30,
                    handler: function(b,e) {
                        yt_rpc.ExtDirectREPL.execute(
                            {code:python_varname + '.pan_rel((0.5, 0.0))'},
                        handle_payload); 
                    }
                }, {
                    xtype:'button',
                    text: 'South',
                    x: 30,
                    y: 50,
                    handler: function(b,e) {
                        yt_rpc.ExtDirectREPL.execute(
                            {code:python_varname + '.pan_rel((0.0, 0.5))'},
                        handle_payload); 
                    }
                }, {
                    xtype: 'button',
                    text: 'West',
                    x: 10,
                    y: 30,
                    handler: function(b,e) {
                        yt_rpc.ExtDirectREPL.execute(
                            {code:python_varname + '.pan_rel((-0.5, 0.0))'},
                        handle_payload); 
                    }
                },
                /* Now the zoom buttons */
                {
                    xtype: 'button',
                    text: 'Zoom In 10x',
                    x: 10,
                    y: 110,
                    width: 80,
                    handler: function(b,e) {
                        yt_rpc.ExtDirectREPL.execute(
                            {code:python_varname + '.zoom(10.0)'},
                        handle_payload); 
                    }
                },{
                    xtype: 'button',
                    text: 'Zoom In 2x',
                    x: 10,
                    y: 135,
                    width: 80,
                    handler: function(b,e) {
                        yt_rpc.ExtDirectREPL.execute(
                            {code:python_varname + '.zoom(2.0)'},
                        handle_payload); 
                    }
                },{
                    xtype: 'button',
                    text: 'Zoom Out 2x',
                    x: 10,
                    y: 160,
                    width: 80,
                    handler: function(b,e) {
                        yt_rpc.ExtDirectREPL.execute(
                            {code:python_varname + '.zoom(0.5)'},
                        handle_payload); 
                    }
                },{
                    xtype: 'button',
                    text: 'Zoom Out 10x',
                    x: 10,
                    y: 185,
                    width: 80,
                    handler: function(b,e) {
                        yt_rpc.ExtDirectREPL.execute(
                            {code:python_varname + '.zoom(0.1)'},
                        handle_payload); 
                    }
                }
            ]
        }
    );

    viewport.get("center-panel").activate("pw_" + this.id);
    viewport.doLayout();
    this.panel = viewport.get("center-panel").get("pw_" + python_varname);
    this.panel.doLayout();
    this.image_panel = this.panel.get("image_panel_"+python_varname);

    this.accept_results = function(payload) {
        this.image_panel.el.dom.src = "data:image/png;base64," + payload['image_data'];
    }

    yt_rpc.ExtDirectREPL.execute(
        {code:python_varname + '.zoom(1.0)'},
        handle_payload);
}

widget_types['plot_window'] = WidgetPlotWindow;
