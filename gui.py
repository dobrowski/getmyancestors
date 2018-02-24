#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from tkinter import Tk, StringVar, IntVar, filedialog, messagebox, Menu, TclError
from tkinter.ttk import Frame, Label, Entry, Button, Checkbutton, Treeview
from getmyancestors import Session, Tree
import asyncio
import re


# Entry widget with right-clic menu to copy/cut/paste
class EntryWithMenu(Entry):
    def __init__(self, master, **kw):
        super(EntryWithMenu, self).__init__(master, **kw)
        self.bind('<Button-3>', self.clic_right)

    def clic_right(self, event):
        menu = Menu(self, tearoff=0)
        try:
            self.selection_get()
            state = 'normal'
        except TclError:
            state = 'disabled'
        menu.add_command(label='Copy', command=self.copy, state=state)
        menu.add_command(label='Cut', command=self.cut, state=state)
        menu.add_command(label='Paste', command=self.paste)
        menu.post(event.x_root, event.y_root)

    def copy(self):
        self.clipboard_clear()
        text = self.selection_get()
        self.clipboard_append(text)

    def cut(self):
        self.copy()
        self.delete('sel.first', 'sel.last')

    def paste(self):
        try:
            text = self.selection_get(selection='CLIPBOARD')
            self.insert('insert', text)
        except TclError:
            pass


class SignIn(Frame):

    def __init__(self, window, **kwargs):
        super(SignIn, self).__init__(window, **kwargs)
        self.username = StringVar()
        self.password = StringVar()
        label_username = Label(self, text='Username:')
        entry_username = EntryWithMenu(self, textvariable=self.username, width=30)
        label_password = Label(self, text='Password:')
        entry_password = EntryWithMenu(self, show='●', textvariable=self.password, width=30)
        label_username.grid(row=0, column=0, pady=15, padx=(0, 5))
        entry_username.grid(row=0, column=1)
        label_password.grid(row=1, column=0, padx=(0, 5))
        entry_password.grid(row=1, column=1)
        entry_username.focus_set()
        entry_username.bind('<Key>', self.enter)
        entry_password.bind('<Key>', self.enter)

    def enter(self, evt):
        if evt.keysym == 'Return':
            self.master.master.login()


class StartIndis(Treeview):
    def __init__(self, window, **kwargs):
        super(StartIndis, self).__init__(window, selectmode='extended', columns=('fid'), **kwargs)
        # self['columns'] = ('fid')
        self.column('fid', width=80)
        self.indis = dict()
        self.heading('fid', text='Id')
        self.bind('<Button-3>', self.popup)

    def add_indi(self, fid):
        if not fid:
            return
        if fid in self.indis.values():
            messagebox.showinfo(message='ID already exist')
            return
        if not re.match(r'[A-Z0-9]{4}-[A-Z0-9]{3}', fid):
            messagebox.showinfo(message='Invalid FamilySearch ID: ' + fid)
            return
        try:
            fs = self.master.master.master.fs
            data = fs.get_url('/platform/tree/persons/%s.json' % fid)
            if data and 'persons' in data:
                if 'names' in data['persons'][0]:
                    for name in data['persons'][0]['names']:
                        if name['preferred']:
                            self.indis[self.insert('', 0, text=name['nameForms'][0]['fullText'], values=fid)] = fid
                            return True
            messagebox.showinfo(message='Individual not found')
        except AttributeError:
            messagebox.showinfo(message='Fatal error: FamilySearch session not found')

    def popup(self, event):
        item = self.identify_row(event.y)
        if item:
            menu = Menu(self, tearoff=0)
            menu.add_command(label='Remove', command=self.delete_item(item))
            menu.post(event.x_root, event.y_root)

    def delete_item(self, item):
        def delete():
            self.indis.pop(item)
            self.delete(item)
        return delete


class Options(Frame):
    def __init__(self, window, ordinances=False, **kwargs):
        super(Options, self).__init__(window, **kwargs)
        self.ancestors = IntVar()
        self.ancestors.set(4)
        self.descendants = IntVar()
        self.spouses = IntVar()
        self.ordinances = IntVar()
        self.contributors = IntVar()
        self.start_indis = StartIndis(self, height=5)
        self.fid = StringVar()
        btn = Frame(self)
        entry_fid = EntryWithMenu(btn, textvariable=self.fid, width=16)
        entry_fid.bind('<Key>', self.enter)
        label_ancestors = Label(self, text='Number of generations to ascend')
        entry_ancestors = EntryWithMenu(self, textvariable=self.ancestors, width=5)
        label_descendants = Label(self, text='Number of generations to descend')
        entry_descendants = EntryWithMenu(self, textvariable=self.descendants, width=5)
        btn_add_indi = Button(btn, text='Add a Familysearch ID', command=self.add_indi)
        btn_spouses = Checkbutton(self, text='          Add spouses and couples information', variable=self.spouses)
        btn_ordinances = Checkbutton(self, text='          Add temple information', variable=self.ordinances)
        btn_contributors = Checkbutton(self, text='          Add list of contributors in notes', variable=self.contributors)
        self.start_indis.grid(row=0, sticky='ew', column=0, columnspan=3)
        entry_fid.grid(row=0, column=0, sticky='e')
        btn_add_indi.grid(row=0, column=1, sticky='w')
        btn.grid(row=1, column=0, columnspan=2)
        entry_ancestors.grid(row=2, column=0, sticky='w')
        label_ancestors.grid(row=2, column=1, sticky='w')
        entry_descendants.grid(row=3, column=0, sticky='w')
        label_descendants.grid(row=3, column=1, sticky='w')
        btn_spouses.grid(row=4, column=0, columnspan=2, sticky='w')
        if ordinances:
            btn_ordinances.grid(row=5, column=0, columnspan=3, sticky='w')
        btn_contributors.grid(row=6, column=0, columnspan=3, sticky='w')
        entry_ancestors.focus_set()

    def add_indi(self):
        if self.start_indis.add_indi(self.fid.get()):
            self.fid.set('')

    def enter(self, evt):
        if evt.keysym == 'Return':
            self.add_indi()


class Gui(Frame):
    def __init__(self, window, **kwargs):
        super(Gui, self).__init__(window, borderwidth=20, **kwargs)
        self.fs = None
        self.tree = None
        self.logfile = open('gui.log', 'w')
        info = Frame(self, borderwidth=10)
        self.info_label = Label(info, borderwidth=20)
        self.form = Frame(self)
        self.sign_in = SignIn(self.form)
        self.options = Options(self.form, True)
        self.title = Label(self, text='Sign In to FamilySearch', font='a 12 bold')
        buttons = Frame(self)
        self.btn_quit = Button(buttons, text='Quit', command=self.quit)
        self.btn_valid = Button(buttons, text='Sign In', command=self.login)
        self.title.pack()
        self.sign_in.pack()
        self.form.pack()
        self.btn_quit.pack(side='left', padx=(0, 40))
        self.btn_valid.pack(side='right', padx=(40, 0))
        self.info_label.pack()
        info.pack()
        buttons.pack()
        self.pack()

    def info(self, text):
        self.info_label.config(text=text)
        self.master.update()

    def save(self):
        filename = filedialog.asksaveasfilename(title='Save as', defaultextension='.ged', filetypes=(('GEDCOM files', '.ged'), ('All files', '*.*')))
        if not filename:
            return
        with open(filename, 'w') as file:
            self.tree.print(file)

    def login(self):
        self.btn_valid.config(state='disabled')
        self.info('Login to FamilySearch...')
        self.fs = Session(self.sign_in.username.get(), self.sign_in.password.get(), verbose=True, logfile=self.logfile, timeout=1)
        if not self.fs.logged:
            messagebox.showinfo(message='The username or password was incorrect')
            self.btn_valid.config(state='normal')
            self.info('')
            return
        self.tree = Tree(self.fs)
        # data = self.fs.get_url('/platform/tree/persons/%s.json' % self.fs.get_userid())
        self.sign_in.destroy()
        self.title.config(text='Options')
        self.btn_valid.config(command=self.download, state='normal', text='Download')
        self.options.pack()
        self.info('')
        self.options.start_indis.add_indi(self.fs.get_userid())

    def download(self):
        todo = [self.options.start_indis.indis[key] for key in sorted(self.options.start_indis.indis)]
        for fid in todo:
            if not re.match(r'[A-Z0-9]{4}-[A-Z0-9]{3}', fid):
                messagebox.showinfo(message='Invalid FamilySearch ID: ' + fid)
                return
        self.options.destroy()
        self.form.destroy()
        _ = self.fs._
        self.btn_valid.config(state='disabled')
        self.info(_('Download starting individuals...'))
        self.tree.add_indis(todo)
        todo = set(todo)
        done = set()
        for i in range(self.options.ancestors.get()):
            if not todo:
                break
            done |= todo
            self.info(_('Download ') + str(i + 1) + _('th generation of ancestors...'))
            todo = self.tree.add_parents(todo) - done

        todo = set(self.tree.indi.keys())
        done = set()
        for i in range(self.options.descendants.get()):
            if not todo:
                break
            done |= todo
            self.info(_('Download ') + str(i + 1) + _('th generation of descendants...'))
            todo = self.tree.add_children(todo) - done

        if self.options.spouses.get():
            self.info('Download spouses and marriage information...')
            todo = set(self.tree.indi.keys())
            self.tree.add_spouses(todo)
        ordi = self.options.ordinances.get()
        cont = self.options.contributors.get()

        async def download_stuff(loop):
            futures = set()
            for fid, indi in self.tree.indi.items():
                futures.add(loop.run_in_executor(None, indi.get_notes))
                if ordi:
                    futures.add(loop.run_in_executor(None, self.tree.add_ordinances, fid))
                if cont:
                    futures.add(loop.run_in_executor(None, indi.get_contributors))
            for fam in self.tree.fam.values():
                futures.add(loop.run_in_executor(None, fam.get_notes))
                if cont:
                    futures.add(loop.run_in_executor(None, fam.get_contributors))
            for future in futures:
                await future

        loop = asyncio.get_event_loop()
        self.info(_('Download notes') + (((',' if cont else _(' and')) + _(' ordinances')) if ordi else '') + (_(' and contributors') if cont else '') + '...')
        loop.run_until_complete(download_stuff(loop))

        self.tree.reset_num()
        self.btn_valid.config(command=self.save, state='normal', text='Save')
        self.info(text='Success. Clic "Save" to save your GEDCOM file.')


window = Tk()
window.title('Getmyancestors')
sign_in = Gui(window)
sign_in.mainloop()
