def QuickRead(path):
    try:
        f = open(path)
        t = f.read()
        f.close()

        return t
    except IOError as e:
        raise errors.Error(str(e))

def Extract(yaml_dict, field_name, type_constraint):
    if field_name not in yaml_dict:
        raise errors.Error('Entry %s is missing' % field_name)

    if not isinstance(yaml_dict[field_name], type_constraint):
        raise errors.Error('Invalid %s entry' % field_name)

    return yaml_dict[field_name]

