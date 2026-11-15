# A module: a Python file whose functions other files can import.
def rupees(amount):
    """Show an amount the Indian way, like 1,23,456."""
    whole = str(int(round(amount)))
    if len(whole) <= 3:
        return "₹" + whole
    head, tail = whole[:-3], whole[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    groups.insert(0, head)
    return "₹" + ",".join(groups) + "," + tail
