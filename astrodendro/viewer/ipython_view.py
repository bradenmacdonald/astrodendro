"""
Backend to the console plugin.

@author: Eitan Isaacson
@organization: IBM Corporation
@copyright: Copyright (c) 2007 IBM Corporation
@license: BSD

All rights reserved. This program and the accompanying materials are made
available under the terms of the BSD which accompanies this distribution, and
is available at U{http://www.opensource.org/licenses/bsd-license.php}
"""
# this file is a modified version of source code from the Accerciser project
# http://live.gnome.org/accerciser

# this file was modified yet again to fix the 'Home' bug - Brian Parma

# Version updated to work with new IPython Embedding API provided by Julian Taylor

import gtk
import re
import sys
import os
import pango
from StringIO import StringIO
from IPython.frontend.terminal.embed import InteractiveShellEmbed

try:
        import IPython
except Exception,e:
        raise ImportError, "Error importing IPython (%s)" % str(e)

#ansi_colors =  {'0;30': 'Black',
#                '0;31': 'Red',
#                '0;32': 'Green',
#                '0;33': 'Brown',
#                '0;34': 'Blue',
#                '0;35': 'Purple',
#                '0;36': 'Cyan',
#                '0;37': 'LightGray',
#                '1;30': 'DarkGray',
#                '1;31': 'DarkRed',
#                '1;32': 'SeaGreen',
#                '1;33': 'Yellow',
#                '1;34': 'LightBlue',
#                '1;35': 'MediumPurple',
#                '1;36': 'LightCyan',
#                '1;37': 'White'}

# Tango Colors (from gnome-terminal)
ansi_colors =  {'0;30': '#2e2e34343636',
                '0;31': '#cccc00000000',
                '0;32': '#4e4e9a9a0606',
                '0;33': '#c4c4a0a00000',
                '0;34': '#34346565a4a4',
                '0;35': '#757550507b7b',
                '0;36': '#060698989a9a',
                '0;37': '#d3d3d7d7cfcf',
                '1;30': '#555557575353',
                '1;31': '#efef29292929',
                '1;32': '#8a8ae2e23434',
                '1;33': '#fcfce9e94f4f',
                '1;34': '#72729f9fcfcf',
                '1;35': '#adad7f7fa8a8',
                '1;36': '#3434e2e2e2e2',
                '1;37': '#eeeeeeeeecec'}

class IterableIPShell:
  def __init__(self,argv=None,user_ns=None,user_global_ns=None,
               cin=None, cout=None,cerr=None, input_func=None):

    if argv is None:
      argv=[]

    # This is to get rid of the blockage that occurs during
    # IPython.Shell.InteractiveShell.user_setup()
    #IPython.iplib.raw_input = lambda x: None

    # not used?
    #self.term = IPython.genutils.IOTerm(cin=cin, cout=cout, cerr=cerr)

    from IPython.config.loader import Config
    cfg = Config()
    cfg.InteractiveShell.colors = "Linux"

    os.environ['TERM'] = 'dumb'
    excepthook = sys.excepthook
    self.IP = InteractiveShellEmbed(config=cfg, user_ns=user_ns, user_global_ns=user_global_ns)

    self.IP.system = lambda cmd: self.shell(self.IP.var_expand(cmd),
                                            header='IPython system call: ',
                                            verbose=self.IP.rc.system_verbose)
    if cin:
      IPython.utils.io.stdin = IPython.utils.io.IOStream(cin)
    if cout:
      IPython.utils.io.stdout = IPython.utils.io.IOStream(cout)
    if cerr:
      IPython.utils.io.stderr = IPython.utils.io.IOStream(cerr)
    if input_func:
      IPython.frontend.terminal.interactiveshell.raw_input_original = input_func
    sys.excepthook = excepthook
    self.iter_more = False
    self.history_level = 0
    self.complete_sep =  re.compile('[\s\{\}\[\]\(\)]')

  def execute(self):
    self.history_level = 0
    orig_stdout = sys.stdout
    line = None
    try:
      if self.IP.autoindent:
        if self.iter_more:
          self.IP.rl_do_indent = True
        else:
          self.IP.rl_do_indent = False
      line = self.IP.raw_input(self.IP.hooks.generate_prompt(self.iter_more))
      if self.IP.autoindent:
        self.IP.rl_do_indent = False
    except KeyboardInterrupt:
      self.IP.write('\nKeyboardInterrupt\n')
      self.IP.input_splitter.reset()
      self.iter_more = False
    except:
      self.IP.showtraceback()
    else:
      sys.stdout = self.cout
      self.IP.input_splitter.push(line)
      self.iter_more = self.IP.input_splitter.push_accepts_more()
      self.prompt = self.IP.hooks.generate_prompt(self.iter_more)
      if not self.iter_more:
        source_raw = self.IP.input_splitter.source_raw_reset()[1]
        self.IP.run_cell(source_raw)
    sys.stdout = orig_stdout

  def historyBack(self):
    self.history_level -= 1
    return self._getHistory()

  def historyForward(self):
    self.history_level += 1
    return self._getHistory()

  def _getHistory(self):
    try:
      rv = self.IP.user_ns['In'][self.history_level].strip('\n')
    except IndexError:
      self.history_level = 0
      rv = ''
    return rv

  def updateNamespace(self, ns_dict):
    self.IP.user_ns.update(ns_dict)

  def complete(self, line):
    split_line = self.complete_sep.split(line)
    possibilities = self.IP.complete(split_line[-1])[1]
    if possibilities:
      common_prefix = reduce(self._commonPrefix, possibilities)
      completed = line[:-len(split_line[-1])]+common_prefix
    else:
      completed = line
    return completed, possibilities

  def _commonPrefix(self, str1, str2):
    for i in range(len(str1)):
      if not str2.startswith(str1[:i+1]):
        return str1[:i]
    return str1

  def shell(self, cmd,verbose=0,debug=0,header=''):
    print 'Shell'
    stat = 0
    if verbose or debug: print header+cmd
    # flush stdout so we don't mangle python's buffering
    if not debug:
      input, output = os.popen4(cmd)
      print output.read()
      output.close()
      input.close()

class ConsoleView(gtk.TextView):
  def __init__(self):
    gtk.TextView.__init__(self)
    self.modify_font(pango.FontDescription('Mono'))
    self.set_cursor_visible(True)
    self.text_buffer = self.get_buffer()
    self.mark = self.text_buffer.create_mark('scroll_mark',
                                             self.text_buffer.get_end_iter(),
                                             False)
    for code in ansi_colors:
      self.text_buffer.create_tag(code,
                                  foreground=ansi_colors[code],
                                  weight=700)
    self.text_buffer.create_tag('0')
    self.text_buffer.create_tag('notouch', editable=False)
    self.color_pat = re.compile('\x01?\x1b\[(.*?)m\x02?')
    self.line_start = \
                self.text_buffer.create_mark('line_start',
                        self.text_buffer.get_end_iter(), True
                )
    self.connect('key-press-event', self._onKeypress)
    self.last_cursor_pos = 0

  def write(self, text, editable=False):
    segments = self.color_pat.split(text)
    segment = segments.pop(0)
    start_mark = self.text_buffer.create_mark(None,
                                              self.text_buffer.get_end_iter(),
                                              True)
    self.text_buffer.insert(self.text_buffer.get_end_iter(), segment)

    if segments:
      ansi_tags = [str(t) for t in self.color_pat.findall(text)]
      print("segments: {0}\nansi_tags: {1}".format(segments, ansi_tags))
      for tag in ansi_tags:
        i = segments.index(tag)
        print("insert_with_tags_by_name(iter, {0}, {1})".format(segments[i+1], tag))
        self.text_buffer.insert_with_tags_by_name(self.text_buffer.get_end_iter(),
                                             segments[i+1], tag)
        segments.pop(i)
    if not editable:
      self.text_buffer.apply_tag_by_name('notouch',
                                         self.text_buffer.get_iter_at_mark(start_mark),
                                         self.text_buffer.get_end_iter())
    self.text_buffer.delete_mark(start_mark)
    self.scroll_mark_onscreen(self.mark)

  def showPrompt(self, prompt):
    self.write(prompt)
    self.text_buffer.move_mark(self.line_start,self.text_buffer.get_end_iter())

  def changeLine(self, text):
    iter = self.text_buffer.get_iter_at_mark(self.line_start)
    iter.forward_to_line_end()
    self.text_buffer.delete(self.text_buffer.get_iter_at_mark(self.line_start), iter)
    self.write(text, True)

  def getCurrentLine(self):
    rv = self.text_buffer.get_slice(self.text_buffer.get_iter_at_mark(self.line_start),
                                    self.text_buffer.get_end_iter(), False)
    return rv

  def showReturned(self, text):
    iter = self.text_buffer.get_iter_at_mark(self.line_start)
    iter.forward_to_line_end()
    self.text_buffer.apply_tag_by_name('notouch',
                                       self.text_buffer.get_iter_at_mark(self.line_start),
                                       iter)
    self.write('\n'+text)
    if text:
      self.write('\n')
    self.showPrompt(self.prompt)
    self.text_buffer.move_mark(self.line_start,self.text_buffer.get_end_iter())
    self.text_buffer.place_cursor(self.text_buffer.get_end_iter())

  def _onKeypress(self, obj, event):
    keys = [gtk.keysyms.Delete,gtk.keysyms.Home,gtk.keysyms.BackSpace,
            gtk.keysyms.End]   # catch these keys
    if (not event.string) and (not event.keyval in keys):
      return
    insert_mark = self.text_buffer.get_insert()
    insert_iter = self.text_buffer.get_iter_at_mark(insert_mark)
    selection_mark = self.text_buffer.get_selection_bound()
    selection_iter = self.text_buffer.get_iter_at_mark(selection_mark)
    start_iter = self.text_buffer.get_iter_at_mark(self.line_start)
    if event.keyval == gtk.keysyms.Home :
        self.text_buffer.place_cursor(start_iter)
        return True # stop other handlers
    if start_iter.compare(insert_iter) <= 0 and \
          start_iter.compare(selection_iter) <= 0:
        return
    if event.keyval == gtk.keysyms.BackSpace:
        self.text_buffer.place_cursor(self.text_buffer.get_end_iter())
        return
    elif start_iter.compare(insert_iter) > 0 and \
          start_iter.compare(selection_iter) > 0:
        self.text_buffer.place_cursor(start_iter)
    elif insert_iter.compare(selection_iter) < 0:
        self.text_buffer.move_mark(insert_mark, start_iter)
    elif insert_iter.compare(selection_iter) > 0:
        self.text_buffer.move_mark(selection_mark, start_iter)



class IPythonView(ConsoleView, IterableIPShell):
  def __init__(self):
    ConsoleView.__init__(self)
    self.cout = StringIO()
    IterableIPShell.__init__(self, cout=self.cout,cerr=self.cout,
                             input_func=self.raw_input)
    self.connect('key_press_event', self.keyPress)
    #self.execute()
    self.cout.truncate(0)
    self.prompt = self.IP.hooks.generate_prompt(self.iter_more)
    self.showPrompt(self.prompt)
    self.interrupt = False

  def raw_input(self, prompt=''):
    if self.interrupt:
      self.interrupt = False
      raise KeyboardInterrupt
    return self.getCurrentLine()

  def keyPress(self, widget, event):
    if event.state & gtk.gdk.CONTROL_MASK and event.keyval == 99:
      self.interrupt = True
      self._processLine()
      return True
    elif event.keyval == gtk.keysyms.Return:
      self._processLine()
      return True
    elif event.keyval == gtk.keysyms.Up:
      self.changeLine(self.historyBack())
      return True
    elif event.keyval == gtk.keysyms.Down:
      self.changeLine(self.historyForward())
      return True
    elif event.keyval == gtk.keysyms.Tab:
      if not self.getCurrentLine().strip():
        # No current line so display non-hidden locals:
        possibilities = [k for k in sorted(self.IP.user_ns.keys()) if k[0] != "_"]
        if len(possibilities) > 1:
          self.write('\n')
          for symbol in possibilities:
            self.write(symbol+'\n')
          self.showPrompt(self.prompt)
        self.changeLine("")
        return True
      else:
        completed, possibilities = self.complete(self.getCurrentLine())
        if len(possibilities) > 1:
          slice = self.getCurrentLine()
          self.write('\n')
          for symbol in possibilities:
            self.write(symbol+'\n')
          self.showPrompt(self.prompt)
        self.changeLine(completed or slice)
        return True

  def _processLine(self):
    self.history_pos = 0
    self.execute()
    rv = self.cout.getvalue()
    if rv: rv = rv.strip('\n')
    self.showReturned(rv)
    self.cout.truncate(0)
