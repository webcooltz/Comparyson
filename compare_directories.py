# compare_directories.py
# - Compares two directories and shows similarities and differences in a GUI
# - Opens a new window with tabs to compare conflicting files

import filecmp
import difflib
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog as fd
from tkinter import *
from tkinter import messagebox


def select_directory_1():
    """ opens a dialog to select directory 1 """
    directory_name = fd.askdirectory()
    if directory_name:
        d1_text.set(directory_name)


def select_directory_2():
    """ opens a dialog to select directory 2 """
    directory_name = fd.askdirectory()
    if directory_name:
        d2_text.set(directory_name)
    if directory_name == d1_text.get():
        messagebox.showwarning("Invalid Selection", "Directory 2 cannot be the same as Directory 1.")
        d2_text.set("")  # clear invalid selection
    else:
        d2_text.set(directory_name)


def compare_directories():
    """ 
    Compare two directories deeply:
        1. Finds similarly-named files
        2. Finds files with identical contents
        3. Finds files with differing contents
        4. Finds similarly-named directories
    Opens a new window with tabs to compare differing files.
    """
    # get comparison result
    result = filecmp.dircmp(d1_text.get(), d2_text.get())

    # matching and differing file lists
    result_matching_name_list.set(str(result.common))
    result_identical_list.set(str(result.same_files))
    result_conflicting_list.set(str(result.diff_files))

    # find differing files (only in one directory)
    diff_array_1 = [f for f in result.left_list if f not in result.right_list]
    diff_array_2 = [f for f in result.right_list if f not in result.left_list]
    result_diff_files_list_1.set(str(diff_array_1))
    result_diff_files_list_2.set(str(diff_array_2))

    # --------------- new window with tabs to compare conflicting files -------------
    conflicting_files = result.diff_files

    if not conflicting_files:
        messagebox.showinfo("No Differences", "No conflicting files found.")
        return

    # new window
    new_window = Toplevel(window)
    new_window.title("Compare Conflicting Files")
    new_window.geometry("900x600")

    # create a notebook (tabbed interface)
    notebook = ttk.Notebook(new_window)
    notebook.pack(fill=BOTH, expand=True)

    # create a new tab for each file comparison
    for file in conflicting_files:
        with open(d1_text.get() + "/" + file, "r", encoding="utf-8", errors="ignore") as f1, \
             open(d2_text.get() + "/" + file, "r", encoding="utf-8", errors="ignore") as f2:
            lines1 = f1.readlines()
            lines2 = f2.readlines()

        # Create frame for the tab
        new_frame = ttk.Frame(notebook)
        notebook.add(new_frame, text=file)

        # ---Left side (directory 1)---
        frame_left = ttk.Frame(new_frame)
        frame_left.pack(side=LEFT, fill='both', expand=True, padx=5, pady=5)
        title1 = ttk.Label(frame_left, text="Directory 1", font=('Arial', 10, 'bold'))
        title1.pack(side=TOP, anchor="w")

        text_frame_left = ttk.Frame(frame_left)
        text_frame_left.pack(fill='both', expand=True)

        text_left = tk.Text(text_frame_left, wrap="none", font=("Consolas", 9), undo=True)
        text_left.pack(side="left", fill="both", expand=True)

        # Scrollbars for left text
        scrollbar_y_left = ttk.Scrollbar(text_frame_left, orient="vertical", command=text_left.yview)
        scrollbar_y_left.pack(side="right", fill="y")
        scrollbar_x_left = ttk.Scrollbar(frame_left, orient="horizontal", command=text_left.xview)
        scrollbar_x_left.pack(side="bottom", fill="x")

        text_left.config(yscrollcommand=scrollbar_y_left.set, xscrollcommand=scrollbar_x_left.set)

        # ---Right side (directory 2)---
        frame_right = ttk.Frame(new_frame)
        frame_right.pack(side=RIGHT, fill='both', expand=True, padx=5, pady=5)
        title2 = ttk.Label(frame_right, text="Directory 2", font=('Arial', 10, 'bold'))
        title2.pack(side=TOP, anchor="w")

        text_frame_right = ttk.Frame(frame_right)
        text_frame_right.pack(fill='both', expand=True)

        text_right = tk.Text(text_frame_right, wrap="none", font=("Consolas", 9), undo=True)
        text_right.pack(side="left", fill="both", expand=True)

        # Scrollbars for right text
        scrollbar_y_right = ttk.Scrollbar(text_frame_right, orient="vertical", command=text_right.yview)
        scrollbar_y_right.pack(side="right", fill="y")
        scrollbar_x_right = ttk.Scrollbar(frame_right, orient="horizontal", command=text_right.xview)
        scrollbar_x_right.pack(side="bottom", fill="x")

        text_right.config(yscrollcommand=scrollbar_y_right.set, xscrollcommand=scrollbar_x_right.set)

        # ------------- Highlight differences using difflib -------------
        differ = difflib.Differ()
        diff = list(differ.compare(lines1, lines2))

        # Add tag styles
        text_left.tag_configure("removed", background="#ffcccc")  # light red
        text_right.tag_configure("added", background="#ccffcc")   # light green
        text_left.tag_configure("changed", background="#fff2cc")  # light yellow
        text_right.tag_configure("changed", background="#fff2cc")

        # Fill both text boxes, tagging differences
        for line in diff:
            code = line[:2]
            content = line[2:]

            if code == "- ":
                # Line only in left file
                text_left.insert(END, content, "removed")
            elif code == "+ ":
                # Line only in right file
                text_right.insert(END, content, "added")
            elif code == "? ":
                # Context line showing change details - skip
                continue
            else:
                # Common line
                text_left.insert(END, content)
                text_right.insert(END, content)

        text_left.config(state="disabled")
        text_right.config(state="disabled")


def reset_fields():
    """Resets all displayed results and text fields."""
    if messagebox.askyesno("Confirm Reset", "Clear all fields?"):
        d1_text.set("")
        d2_text.set("")
        result_matching_name_list.set("")
        result_conflicting_list.set("")
        result_identical_list.set("")
        result_diff_files_list_1.set("")
        result_diff_files_list_2.set("")
        d1_result_diff_files.set("")
        d2_result_diff_files.set("")


# ---Main GUI---

window = tk.Tk()
window.geometry("500x300")
window.title("Comparyson")

# StringVars (to hold text values for labels)
d1_text = tk.StringVar()
d2_text = tk.StringVar()
result_matching_name_list = tk.StringVar()
result_conflicting_list = tk.StringVar()
result_identical_list = tk.StringVar()
result_diff_files_list_1 = tk.StringVar()
result_diff_files_list_2 = tk.StringVar()
d1_result_diff_files = tk.StringVar()
d2_result_diff_files = tk.StringVar()

# ---buttons to open directories---

# open directory 1 picker
open_directory1_button = ttk.Button(
    window,
    text='Open Directory',
    command=select_directory_1
)
open_directory1_button.grid(row=0, column=2)

# open directory 2 picker
open_directory2_button = ttk.Button(
    window,
    text='Open Directory',
    command=select_directory_2
)
open_directory2_button.grid(row=1, column=2)

# labels for selected directories
tk.Label(window, text="Directory 1:").grid(row=0)
tk.Label(window, text="Directory 2:").grid(row=1)
d1 = tk.Label(window, textvariable=d1_text).grid(row=0, column=1)
d2 = tk.Label(window, textvariable=d2_text).grid(row=1, column=1)

# button to call compare_directories()
compare_button = ttk.Button(
    window,
    text='Compare',
    command=compare_directories
)
compare_button.grid(row=3, column=1, sticky=tk.W, pady=4)

# button to call reset_fields()
reset_button = ttk.Button(
    window,
    text='Reset',
    command=reset_fields
)
reset_button.grid(row=4, column=1, sticky=tk.W, pady=4)

# labels for the result fields
tk.Label(window, text="Same file names:").grid(row=5)
tk.Label(window, text="Identical files:").grid(row=6)
tk.Label(window, text="Conflicting Files:").grid(row=7)
tk.Label(window, text="Different Files (d1):").grid(row=8)
tk.Label(window, text="Different Files (d2):").grid(row=9)
# tk.Label(window, text="Errors:").grid(row=10)

# result fields
match_answer_label = tk.Label(window, textvariable=result_matching_name_list).grid(row=5, column=1)
identical_answer_label = tk.Label(window, textvariable=result_identical_list).grid(row=6, column=1)
conflicting_files_label = tk.Label(window, textvariable=result_conflicting_list).grid(row=7, column=1)
diff_files_label_1 = tk.Label(window, textvariable=result_diff_files_list_1).grid(row=8, column=1)
diff_files_label_2 = tk.Label(window, textvariable=result_diff_files_list_2).grid(row=9, column=1)

# printed file labels
# tk.Label(window, text="d1 file:").grid(row=10, column=0)
# tk.Label(window, text="d2 file:").grid(row=10, column=1)
# d1_diff_file_label = tk.Label(window, textvariable=d1_result_diff_files).grid(row=11, column=0)
# d2_diff_file_label = tk.Label(window, textvariable=d2_result_diff_files).grid(row=11, column=1)

window.mainloop()
tk.mainloop()

# test strings for directories
# D:/projects-coding/python/python-comparison/d1
# D:/projects-coding/python/python-comparison/d2

# TODO - Clean up tabs to make it look nicer
# TODO - Add links from each file to open up? In a new tab or in file explorer
# TODO - List subdirectories/ their files and compare those
# TODO - Add error handling
# TODO - Add limits to prevent memory leaks, crashes, etc.
# TODO - Prevent from being run multiple times? -- It may be fixed
