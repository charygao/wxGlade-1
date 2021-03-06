"""\
Classes to handle and display the structure of a wxGlade app

@copyright: 2002-2007 Alberto Griggio
@copyright_ 2014-2016 Carsten Grohmann
@license: MIT (see LICENSE.txt) - THIS PROGRAM COMES WITH NO WARRANTY
"""

import logging
import os.path
import sys
import StringIO
import time
import types
import wx

import misc
import common
import compat
import config


class SlotNode(object):
    """\
    To write a placeholder for an empty sizer slot
    """

    def write(self, outfile, tabs):
        stmt = common.format_xml_tag(
            u'object', '', tabs, **{'class': 'sizerslot'})
        outfile.write(stmt)


class Tree(object):
    """\
    A class to represent a hierarchy of widgets.

    @ivar _logger: Class specific logging instance
    """
    class Node(object):
        __empty_win = None

        def __init__(self, widget=None, children=None):
            self.widget = widget
            self.children = children
            self.parent = None

        def remove(self):
            def remove_rec(node):
                if node.children is not None:
                    map(remove_rec, node.children)
                node.children = None
                if node.widget is not None:
                    # replace the just destroyed notebook with an empty window
                    pw = node.widget.property_window
                    pw.SetTitle(_('Properties - <%s>') % '')
                    if Tree.Node.__empty_win is None:
                        Tree.Node.__empty_win = wx.Window(pw, -1)
                    compat.SizerItem_SetWindow(
                        pw.GetSizer().GetChildren()[0],
                        Tree.Node.__empty_win,
                        )
                    # call the widget's ``destructor''
                    node.widget.delete()
                node.widget = None
            remove_rec(self)
            try:
                self.parent.children.remove(self)
            except:
                pass

        def __repr__(self):
            try: return self.widget.name
            except AttributeError: return repr(self.widget)

        def write(self, outfile, tabs, class_names=None):
            """\
            Writes the xml code for the widget to the given output file
            """
            import edit_sizers
            fwrite = outfile.write
            assert self.widget is not None
            classname = getattr(self.widget, '_classname',
                                self.widget.__class__.__name__)
            # to disable custom class code generation (for panels...)
            if getattr(self.widget, 'no_custom_class', False):
                no_custom = u' no_custom_class="1"'
            else:
                no_custom = ""
            outer_tabs = u'    ' * tabs
            fwrite(u'%s<object %s %s %s%s>\n' % (
                outer_tabs,
                common.format_xml_attrs(**{'class': self.widget.klass}),
                common.format_xml_attrs(name=self.widget.name),
                common.format_xml_attrs(base=classname),
                no_custom))

            for prop in self.widget.properties:
                if not getattr(self.widget.properties[prop], '_omitter',
                               None):
                    self.write_by_omitter(self.widget, prop, outfile,
                                          tabs + 1)

            if class_names is not None and \
                            self.widget.__class__.__name__ != 'CustomWidget':
                class_names.add(self.widget.klass)

            # sort children by sizer position and add "sizerlots" for empty
            # positions
            if isinstance(self.widget, edit_sizers.SizerBase):
                # number of sizer slots from parent object
                sizer_slots = len(self.widget.children)

                # children = self.children is not None and self.children or []
                children = self.children or []

                # create list of children / "sizerslots" based on sizer
                # position
                children_by_position = {}
                for child in children:
                    children_by_position[child.widget.pos] = child

                # convert back to list
                children = [children_by_position.get(pos, SlotNode())
                            for pos in range(1, sizer_slots)]

                for child in children:
                    if hasattr(child, 'widget'):
                        inner_xml = StringIO.StringIO()
                        for prop in child.widget.sizer_properties.values():
                            prop.write(inner_xml, tabs + 2)
                        child.write(inner_xml, tabs + 2, class_names)
                        stmt = common.format_xml_tag(
                            u'object', inner_xml.getvalue(), tabs + 1,
                            is_xml=True, **{'class': 'sizeritem'}
                        )
                        fwrite(stmt)
                    else:
                        child.write(outfile, tabs + 1)
            elif self.children is not None:
                for child in self.children:
                    child.write(outfile, tabs + 1, class_names)
            fwrite(u'%s</object>\n' % outer_tabs)

        def write_by_omitter(self, widget, name, file, tabs):
            """\
            Write to given output file:
            - value of property
            - values of properties that previous can block
            - any omitter can be blocked as well
            """
            widget.properties[name].write(file, tabs)
            if getattr(widget, 'get_property_blocking', None):
                items = widget.get_property_blocking(name)
                if items:
                    for name in items:
                        self.write_by_omitter(widget, name, file, tabs)

    # end of class Node

    def __init__(self, root=None, app=None):
        # initialise instance logger
        self._logger = logging.getLogger(self.__class__.__name__)

        # initialise instance
        self.root = root
        if self.root is None: self.root = Tree.Node()
        self.current = self.root
        self.app = app  # reference to the app properties
        self.names = {}  # dictionary of names of the widgets: each entry is
                        # itself a dictionary, one for each toplevel widget...

    def _find_toplevel(self, node):
        assert node is not None, _("None node in _find_toplevel")
        if node.parent is self.root:
            return node
        while node.parent is not self.root:
            node = node.parent
        return node

    def has_name(self, name, node=None):
        if node is None:
            #self._logger.debug('name to check: %s', name)
            for n in self.names:
                #self._logger.debug(
                #    'names of %s: %s',
                #    n.widget.name,
                #    self.names[n]
                #)
                if name in self.names[n]:
                    return True
            return False
        else:
            node = self._find_toplevel(node)
            #self._logger.debug('name to check: %s', name)
            #self._logger.debug(
            #    'names of node %s: %s',
            #    node.widget.name,
            #    self.names[node]
            #    )
            return name in self.names[node]
        #return self.names.has_key(name)

    def add(self, child, parent=None):
        if parent is None: parent = self.root
        if parent.children is None: parent.children = []
        parent.children.append(child)
        child.parent = parent
        self.current = child
        #self.names[str(child.widget.name)] = 1
        #self.names.setdefault(parent, {})[str(child.widget.name)] = 1
        self.names.setdefault(self._find_toplevel(child), {})[
            str(child.widget.name)] = 1
        if parent is self.root and \
               getattr(child.widget.__class__, '_is_toplevel', False):
            self.app.add_top_window(child.widget.name)

    def insert(self, child, parent, index):
        if parent is None: parent = self.root
        if parent.children is None:
            parent.children = []
        parent.children.insert(index, child)
        child.parent = parent
        self.current = child
        #self.names[str(child.widget.name)] = 1
        #self.names.setdefault(parent, {})[str(child.widget.name)] = 1
        self.names.setdefault(self._find_toplevel(child), {})[
            str(child.widget.name)] = 1
        if parent is self.root:
            self.app.add_top_window(child.widget.name)

    def remove(self, node=None):
        if node is not None:
            def clear_name(n):
                try:
                    #del self.names[str(n.widget.name)]
                    del self.names[self._find_toplevel(n)][str(n.widget.name)]
                except (KeyError, AttributeError):
                    pass
                if n.children:
                    for c in n.children: clear_name(c)
            clear_name(node)
            if node.parent is self.root:
                self.app.remove_top_window(node.widget.name)
            node.remove()
        elif self.root.children:
            for n in self.root.children:
                n.remove()
            self.root.children = None
            self.names = {}

    def write(self, outfile=None, tabs=0):
        """\
        Writes the xml equivalent of this tree to the given output file.

        This function writes unicode to the outfile.
        """
        if outfile is None:
            outfile = sys.stdout
        outfile.write(u'<?xml version="1.0"?>\n'
                      u'<!-- generated by wxGlade %s on %s -->\n\n' %
                      (config.version, time.asctime()))
        outpath = os.path.normpath(
            os.path.expanduser(self.app.output_path.strip()))
        name = self.app.get_name()
        klass = self.app.get_class()
        option = self._to_digit_string(self.app.multiple_files)
        top_window = self.app.get_top_window()
        language = self.app.get_language()
        encoding = self.app.get_encoding()
        use_gettext = self._to_digit_string(self.app.use_gettext)
        is_template = self._to_digit_string(self.app.is_template)
        overwrite = self._to_digit_string(self.app.overwrite)
        indent_amount = self._to_digit_string(self.app.indent_amount)
        indent_symbol = self._to_digit_string(self.app.indent_mode)
        if indent_symbol == '0':
            indent_symbol = u"tab"
        else:
            indent_symbol = u"space"
        source_ext = '.' + self.app.source_ext
        header_ext = '.' + self.app.header_ext
        for_version = str(self.app.for_version)

        attrs = {
            'path': outpath,
            'name': name,
            'class': klass,
            'option': option,
            'language': language,
            'top_window': top_window,
            'encoding': encoding,
            'use_gettext': use_gettext,
            'overwrite': overwrite,
            'use_new_namespace': 1,
            'for_version': for_version,
            'is_template': is_template,
            'indent_amount': indent_amount,
            'indent_symbol': indent_symbol,
            'source_extension': source_ext,
            'header_extension': header_ext,
        }

        inner_xml = StringIO.StringIO()

        if self.app.is_template and getattr(self.app, 'template_data', None):
            self.app.template_data.write(inner_xml, tabs + 1)

        class_names = set()
        if self.root.children is not None:
            for c in self.root.children:
                c.write(inner_xml, tabs + 1, class_names)

        stmt = common.format_xml_tag(
            u'application', inner_xml.getvalue(), is_xml=True, **attrs)
        outfile.write(stmt)

        return class_names

    def change_node(self, node, widget):
        """\
        Changes the node 'node' so that it refers to 'widget'
        """
        try:
            #del self.names[node.widget.name]
            del self.names[self._find_toplevel(node)][node.widget.name]
        except KeyError:
            pass
        node.widget = widget
        #self.names[widget.name] = 1
        self.names.setdefault(self._find_toplevel(node), {})[widget.name] = 1

    def change_node_pos(self, node, new_pos, index=None):
        if index is None: index = node.parent.children.index(node)
        if index >= new_pos:
            node.parent.children.insert(new_pos, node)
            del node.parent.children[index + 1]
        else:
            del node.parent.children[index]
            node.parent.children.insert(new_pos+1, node)

    def _to_digit_string(self, value):
        """\
        Convert the given value to a digit string.

        @param value: Value to convert
        @type value: str|int|bool

        @rtype: str
        """
        if isinstance(value, types.BooleanType):
            if value:
                return '1'
            else:
                return '0'
        elif isinstance(value, types.IntType):
            return '%s' % value
        elif isinstance(value, types.StringTypes):
            if value.isdigit():
                return value

        # log failures
        logging.warning(
            _('Failed to convert "%s" (type: %s) to a digit string'),
            value, type(value))

        return '%s' % value

# end of class Tree


class WidgetTree(wx.TreeCtrl, Tree):
    """\
    Tree with the ability to display the hierarchy of widgets
    """

    images = {}
    """\
    Dictionary of icons of the widgets displayed
    """

    _logger = None
    """\
    Class specific logging instance
    """

    def __init__(self, parent, application):
        self._logger = logging.getLogger(self.__class__.__name__)
        id = wx.NewId()
        style = wx.TR_DEFAULT_STYLE|wx.TR_HAS_VARIABLE_ROW_HEIGHT
        if wx.Platform == '__WXGTK__':
            style |= wx.TR_NO_LINES|wx.TR_FULL_ROW_HIGHLIGHT
        elif wx.Platform == '__WXMAC__':
            style &= ~wx.TR_ROW_LINES
        wx.TreeCtrl.__init__(self, parent, id, style=style)
        root_node = Tree.Node(application)
        self.cur_widget = None  # reference to the selected widget
        Tree.__init__(self, root_node, application)
        image_list = wx.ImageList(21, 21)
        image_list.Add(wx.Bitmap(os.path.join(config.icons_path,
                                             'application.xpm'),
                                wx.BITMAP_TYPE_XPM))
        for w in WidgetTree.images:
##             WidgetTree.images[w] = image_list.Add(wx.Bitmap(
##                 WidgetTree.images[w], wx.BITMAP_TYPE_XPM))
            WidgetTree.images[w] = image_list.Add(
                misc.get_xpm_bitmap(WidgetTree.images[w]))
        self.AssignImageList(image_list)
        root_node.item = self.AddRoot(_('Application'), 0)
        self.SetPyData(root_node.item, root_node)
        self.skip_select = 0  # necessary to avoid an infinite loop on
                              # win32, as SelectItem fires an
                              # EVT_TREE_SEL_CHANGED event
        self.title = ' '
        self.set_title(self.title)

        self.auto_expand = True  # this control the automatic expansion of
                                # nodes: it is set to False during xml loading
        self._show_menu = misc.wxGladePopupMenu('widget')  # popup menu to
                                                          # show toplevel
                                                          # widgets
        self._show_menu.Append(wx.ID_ANY, _('Show'))
        self.Bind(wx.EVT_TREE_SEL_CHANGED, self.on_change_selection)
        self.Bind(wx.EVT_RIGHT_DOWN, self.popup_menu)
        self.Bind(wx.EVT_LEFT_DCLICK, self.show_toplevel)
        self.Bind(wx.EVT_MENU, self.show_toplevel)

        def on_key_down(event):
            evt_flags = 0
            if event.ControlDown():
                evt_flags = wx.ACCEL_CTRL
            evt_key = event.GetKeyCode()
            for flags, key, function in misc.accel_table:
                if evt_flags == flags and evt_key == key:
                    wx.CallAfter(function)
                    break
            event.Skip()
        self.Bind(wx.EVT_KEY_DOWN, on_key_down)

    def _build_label(self, node):
        s = node.widget.name
        if node.widget.klass != node.widget.base and \
               node.widget.klass != 'wxScrolledWindow':  # special case...
            s += ' (%s)' % node.widget.klass
        return s

    def add(self, child, parent=None, image=None):  # is image still used?
        """\
        appends child to the list of parent's children
        """
        Tree.add(self, child, parent)
        name = child.widget.__class__.__name__
        index = WidgetTree.images.get(name, -1)
        if parent is None: parent = parent.item = self.GetRootItem()
        child.item = self.AppendItem(parent.item, self._build_label(child),
                                     index)
        self.SetPyData(child.item, child)
        if self.auto_expand:
            self.Expand(parent.item)
            self.select_item(child)
        child.widget.show_properties()
        self.app.check_codegen(child.widget)

    def insert(self, child, parent, pos, image=None):
        """\
        inserts child to the list of parent's children, before index
        """
        if parent.children is None:
            self.add(child, parent, image)
            return
        name = child.widget.__class__.__name__
        image_index = WidgetTree.images.get(name, -1)
        if parent is None:
            parent = parent.item = self.GetRootItem()

        index = 0
        item, cookie = self.GetFirstChild(parent.item)
        while item.IsOk():
            item_pos = self.GetPyData(item).widget.pos
            if pos < item_pos: break
            index += 1
            item, cookie = self.GetNextChild(parent.item, cookie)

        Tree.insert(self, child, parent, index)
        child.item = self.InsertItemBefore(parent.item, index,
                                           self._build_label(child),
                                           image_index)
        self.SetPyData(child.item, child)
        if self.auto_expand:
            self.Expand(parent.item)
            self.select_item(child)
        child.widget.show_properties()
        self.app.check_codegen(child.widget)

    def remove(self, node=None):
        self.app.saved = False  # update the status of the app
        Tree.remove(self, node)
        if node is not None:
            try:
                self.cur_widget = None
                self.SelectItem(node.parent.item)
            except: self.SelectItem(self.GetRootItem())
            self.Delete(node.item)
        else:
            wx.TreeCtrl.Destroy(self)

    def clear(self):
        self.app.reset()
        self.skip_select = True
        if self.root.children:
            while self.root.children:
                c = self.root.children[-1]
                if c.widget: c.widget.remove()
            self.root.children = None
        self.skip_select = False
        app = self.GetPyData(self.GetRootItem())
        app.widget.show_properties()

    def refresh_name(self, node, oldname=None):  # , name=None):
        if oldname is not None:
            try:
                #del self.names[self.GetItemText(node.item)]
                del self.names[self._find_toplevel(node)][oldname]
            except KeyError:
                pass
        #self.names[name] = 1
        #self.SetItemText(node.item, name)
        #self.names[node.widget.name] = 1
        self.names.setdefault(self._find_toplevel(node), {})[
            node.widget.name] = 1
        self.SetItemText(node.item, self._build_label(node))

    def select_item(self, node):
        self.skip_select = True
        self.SelectItem(node.item)
        self.skip_select = False
        if self.cur_widget: self.cur_widget.update_view(False)
        self.cur_widget = node.widget
        self.cur_widget.update_view(True)
        self.cur_widget.show_properties()
        misc.focused_widget = self.cur_widget

    def on_change_selection(self, event):
        if not self.skip_select:
            item = event.GetItem()
            try:
                if self.cur_widget: self.cur_widget.update_view(False)
                self.cur_widget = self.GetPyData(item).widget
                misc.focused_widget = self.cur_widget
                self.cur_widget.show_properties(None)
                self.cur_widget.update_view(True)
            except AttributeError:
                pass
            except Exception:
                self._logger.exception(_('Internal Error'))

    def popup_menu(self, event):
        node = self._find_item_by_pos(*event.GetPosition())
        if not node:
            return
        self.select_item(node)
        item = node.widget
        if not item.widget or not item.is_visible():
            if node.parent is self.root:
                self._show_menu.SetTitle(item.name)
                self.PopupMenu(self._show_menu, event.GetPosition())
            return
        item.popup_menu(event)

    def expand(self, node=None, yes=True):
        """\
        expands or collapses the given node
        """
        if node is None: node = self.root
        if yes: self.Expand(node.item)
        else: self.Collapse(node.item)

    def set_title(self, value):
        if value is None: value = ""
        self.title = value
        try:
            self.GetParent().SetTitle(_('wxGlade: Tree %s') % value)
        except:
            pass

    def get_title(self):
        if not self.title: self.title = ' '
        return self.title

    def show_widget(self, node, toplevel=False):
        """\
        Shows the widget of the given node and all its children
        """
        if toplevel:
            if not wx.IsBusy():
                wx.BeginBusyCursor()
            if not node.widget.widget:
                node.widget.create_widget()
                node.widget.finish_widget_creation()
            if node.children:
                for c in node.children: self.show_widget(c)
            node.widget.post_load()
            node.widget.show_widget(True)
            node.widget.show_properties()
            node.widget.widget.Raise()
            # set the best size for the widget (if no one is given)
            props = node.widget.properties
            if 'size' in props and not props['size'].is_active() and \
                   node.widget.sizer:
                node.widget.sizer.fit_parent()
            if wx.IsBusy():
                wx.EndBusyCursor()
        else:
            import edit_sizers

            def show_rec(node):
                node.widget.show_widget(True)
                self.expand(node, True)
                if node.children:
                    for c in node.children: show_rec(c)
                node.widget.post_load()
##                 w = node.widget
##                 if isinstance(w, edit_sizers.SizerBase): return
##                 elif not w.properties['size'].is_active() and \
##                          w.sizer and w.sizer.toplevel:
##                     w.sizer.fit_parent()
            show_rec(node)

    def show_toplevel(self, event):
        """\
        Event handler for left double-clicks: if the click is above a toplevel
        widget and this is hidden, shows it
        """
        try: x, y = event.GetPosition()
        except AttributeError:
            # if we are here, event is a CommandEvent and not a MouseEvent
            node = self.GetPyData(self.GetSelection())
            self.expand(node)  # if we are here, the widget must be shown
        else:
            node = self._find_item_by_pos(x, y, True)
        if node is not None:
            if not node.widget.is_visible():
                # added by rlawson to expand node on showing top level widget
                self.expand(node)
                self.show_widget(node, True)
            else:
                node.widget.show_widget(False)
                #self.select_item(self.root)
                # added by rlawson to collapse only the toplevel node,
                # not collapse back to root node
                self.select_item(node)
                self.app.show_properties()
                event.Skip()
        #event.Skip()

    def _find_item_by_pos(self, x, y, toplevels_only=False):
        """\
        Finds the node which is displayed at the given coordinates.
        Returns None if there's no match.
        If toplevels_only is True, scans only root's children
        """
        item, flags = self.HitTest((x, y))
        if item and flags & (wx.TREE_HITTEST_ONITEMLABEL |
                             wx.TREE_HITTEST_ONITEMICON):
            node = self.GetPyData(item)
            if not toplevels_only or node.parent is self.root:
                return node
        return None

    def change_node(self, node, widget):
        Tree.change_node(self, node, widget)
        self.SetItemImage(node.item, self.images.get(
            widget.__class__.__name__, -1))
        self.SetItemText(node.item, self._build_label(node))  # widget.name)

    def change_node_pos(self, node, new_pos):
        if new_pos >= self.GetChildrenCount(node.parent.item, False):
            return
        index = node.parent.children.index(node)
        Tree.change_node_pos(self, node, new_pos, index)
        old_item = node.item
        image = self.GetItemImage(node.item)
        self.Freeze()
        #self._logger.debug(
        #    '%s, %s, %s',
        #    self._build_label(node),
        #    index,
        #    new_pos
        #    )
        if index >= new_pos:
            node.item = self.InsertItemBefore(
                node.parent.item, new_pos, self._build_label(node), image)
        else:
            node.item = self.InsertItemBefore(
                node.parent.item, new_pos+1, self._build_label(node), image)
        self.SetPyData(node.item, node)

        def append(parent, node):
            idx = WidgetTree.images.get(node.widget.__class__.__name__, -1)
            node.item = self.AppendItem(parent.item,
                                        self._build_label(node), idx)
            self.SetPyData(node.item, node)
            if node.children:
                for c in node.children:
                    append(node, c)
            self.Expand(node.item)
        if node.children:
            for c in node.children:
                append(node, c)
        self.Expand(node.item)
        self.Delete(old_item)
        self.Thaw()

    def get_selected_path(self):
        """\
        returns a list of widget names, from the toplevel to the selected one
        Example:
        ['frame_1', 'sizer_1', 'panel_1', 'sizer_2', 'button_1']
        if button_1 is the currently selected widget.
        """
        from edit_sizers import SizerBase
        ret = []
        w = self.cur_widget
        oldw = None
        while w is not None:
            oldw = w
            ret.append(w.name)
            sizer = getattr(w, 'sizer', None)
            if getattr(w, 'parent', "") is None:
                w = w.parent
            elif sizer is not None and not sizer.is_virtual():
                w = sizer
            else:
                if isinstance(w, SizerBase):
                    w = w.window
                else:
                    w = w.parent
        ret.reverse()
        # ALB 2007-08-28: remember also the position of the toplevel window in
        # the selected path
        if oldw is not None:
            assert oldw.widget
            pos = misc.get_toplevel_parent(oldw.widget).GetPosition()
            ret[0] = (ret[0], pos)
        return ret

    def select_path(self, path):
        """\
        sets the selected widget from a path_list, which should be in the
        form returned by get_selected_path
        """
        index = 0
        item, cookie = self._get_first_child(self.GetRootItem())
        itemok = None
        parent = None
        pos = None
        while item.Ok() and index < len(path):
            widget = self.GetPyData(item).widget
            name = path[index]
            if index == 0 and isinstance(name, types.TupleType):
                name, pos = name
            if misc.streq(widget.name, name):
                #self._logger.debug('OK: %s', widget.name)
                #self.EnsureVisible(item)
                itemok = item
                if parent is None:
                    parent = self.GetPyData(itemok)
                self.cur_widget = widget
                item, cookie = self._get_first_child(item)
                index += 1
            else:
                #self._logger.debug('NO: %s', widget.name)
                item = self.GetNextSibling(item)
        if itemok is not None:
            node = self.GetPyData(itemok)
            if parent is not None:
                self.show_widget(parent, True)
                if pos is not None:
                    misc.get_toplevel_parent(parent.widget).SetPosition(pos)
            self.select_item(node)

    def _get_first_child(self, item):
        return self.GetFirstChild(item)

# end of class WidgetTree

