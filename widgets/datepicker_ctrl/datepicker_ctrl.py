"""\
wxDatePickerCtrl objects

@copyright: 2002-2007 Alberto Griggio
@copyright: 2014-2016 Carsten Grohmann
@license: MIT (see LICENSE.txt) - THIS PROGRAM COMES WITH NO WARRANTY
"""

import wx
from edit_windows import ManagedBase, EditStylesMixin
from tree import Tree
import common
import compat
import config
from widget_properties import *


class EditDatePickerCtrl(ManagedBase, EditStylesMixin):
    """\
    Class to handle wxDatePickerCtrl objects
    """

    def __init__(self, name, parent, id, sizer, pos, property_window,
                 show=True):
        # Initialise parent classes
        ManagedBase.__init__(self, name, 'wxDatePickerCtrl', parent, id,
                             sizer, pos, property_window, show=show)
        EditStylesMixin.__init__(self)

        # initialise instance variables
        self.default = False
        if config.preferences.default_border:
            self.border = config.preferences.default_border_size
            self.flag = wx.ALL

        # initialise properties remaining staff
        self.access_functions['default'] = (self.get_default,
                                            self.set_default)
        self.access_functions['style'] = (self.get_style, self.set_style)
        self.properties['default'] = CheckBoxProperty(self, 'default', None, label=_("default"))
        self.properties['style'] = CheckListProperty(
            self, 'style', self.widget_writer)

    def create_properties(self):
        ManagedBase.create_properties(self)
        panel = wx.Panel(self.notebook, -1)
        #self.properties['label'].display(panel)
        self.properties['default'].display(panel)
        self.properties['style'].display(panel)
        szr = wx.BoxSizer(wx.VERTICAL)
        szr.Add(self.properties['default'].panel, 0, wx.EXPAND)
        szr.Add(self.properties['style'].panel, 0, wx.EXPAND)
        panel.SetAutoLayout(1)
        compat.SizerItem_SetSizer(panel, szr)
        szr.Fit(panel)
        self.notebook.AddPage(panel, 'Widget')

    def create_widget(self):
        try:
            # TODO add all the other parameters for the DatePickerCtrl
            # initial date
            self.widget = wx.DatePickerCtrl(self.parent.widget, self.id,
                                            style=self.get_int_style())
        except AttributeError:
            self.widget = wx.DatePickerCtrl(self.parent.widget, self.id)

    def get_default(self):
        return self.default

    def set_default(self, value):
        self.default = bool(int(value))

# end of class EditDatePickerCtrl


def builder(parent, sizer, pos, number=[1]):
    """\
    factory function for EditDatePickerCtrl objects.
    """
    label = 'datepicker_ctrl_%d' % number[0]
    while common.app_tree.has_name(label):
        number[0] += 1
        label = 'datepicker_ctrl_%d' % number[0]
    datepicker_ctrl = EditDatePickerCtrl(label, parent, wx.NewId(), sizer,
                        pos, common.property_panel)
    node = Tree.Node(datepicker_ctrl)
    datepicker_ctrl.node = node
    datepicker_ctrl.show_widget(True)
    common.app_tree.insert(node, sizer.node, pos - 1)


def xml_builder(attrs, parent, sizer, sizeritem, pos=None):
    """\
    factory to build EditDatePickerCtrl objects from a XML file
    """
    from xml_parse import XmlParsingError
    try:
        label = attrs['name']
    except KeyError:
        raise XmlParsingError(_("'name' attribute missing"))
    if sizer is None or sizeritem is None:
        raise XmlParsingError(_("sizer or sizeritem object cannot be None"))
    datepicker_ctrl = EditDatePickerCtrl(label, parent, wx.NewId(), sizer,
                        pos, common.property_panel, show=False)
    sizer.set_item(datepicker_ctrl.pos, option=sizeritem.option,
                   flag=sizeritem.flag, border=sizeritem.border)
    node = Tree.Node(datepicker_ctrl)
    datepicker_ctrl.node = node
    if pos is None:
        common.app_tree.add(node, sizer.node)
    else:
        common.app_tree.insert(node, sizer.node, pos - 1)
    return datepicker_ctrl


def initialize():
    """\
    initialization function for the module.
    @rtype: wxBitmapButton
    @return: an icon to be added to the main palette. 
    """
    common.widgets['EditDatePickerCtrl'] = builder
    common.widgets_from_xml['EditDatePickerCtrl'] = xml_builder

    return common.make_object_button('EditDatePickerCtrl', 'datepicker_ctrl.xpm')
