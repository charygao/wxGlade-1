"""\
Common code for all widget builders

@copyright: 2012-2016 Carsten Grohmann
@license: MIT (see LICENSE.txt) - THIS PROGRAM COMES WITH NO WARRANTY
"""

#XXX siehe auch Klassen WidgetHandler ...


class BaseWidgetBuilder(object):
    """\
    Class to document attributes at the moment only.
    """

    def set_defaults(self):
        """\
        siehe bug mit leeren styles fuer frame und dialog
        """
        pass

    @staticmethod
    def from_xml():
        """\
        Factory to build XXX objects from a XML file
        """
        pass

    @staticmethod
    def from_gui():
        """\
        Factory to build XXX objects triggered from GUI
        """
        pass

# end of class BaseWidgetBuilder
