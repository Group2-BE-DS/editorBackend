class TextOperation:
    def __init__(self):
        self.ops = []  # List of operations (retain, insert, delete)

    @classmethod
    def from_json(cls, data):
        op = cls()
        op.ops = data
        return op

    def to_json(self):
        return self.ops

    def apply(self, content):
        pos = 0
        result = []

        for op in self.ops:
            if isinstance(op, int):  # retain
                result.append(content[pos:pos + op])
                pos += op
            elif isinstance(op, str):  # insert
                result.append(op)
            else:  # delete (negative number)
                pos -= op

        result.append(content[pos:])
        return ''.join(result)

    def compose(self, other):
        """Compose this operation with another operation."""
        result = TextOperation()
        i1, i2 = 0, 0  # Operation indices
        op1, op2 = self.ops, other.ops

        while i1 < len(op1) and i2 < len(op2):
            if isinstance(op1[i1], str):  # Insertion in first operation
                result.ops.append(op1[i1])
                i1 += 1
                continue

            if isinstance(op2[i2], str):  # Insertion in second operation
                result.ops.append(op2[i2])
                i2 += 1
                continue

            # Both ops are retain or delete
            if op1[i1] < 0:  # Delete in first operation
                result.ops.append(op1[i1])
                i1 += 1
                continue

            if op2[i2] < 0:  # Delete in second operation
                result.ops.append(op2[i2])
                i2 += 1
                continue

            # Both are retain operations
            retain1, retain2 = op1[i1], op2[i2]
            if retain1 > retain2:
                result.ops.append(retain2)
                op1[i1] = retain1 - retain2
                i2 += 1
            elif retain1 == retain2:
                result.ops.append(retain1)
                i1 += 1
                i2 += 1
            else:
                result.ops.append(retain1)
                op2[i2] = retain2 - retain1
                i1 += 1

        # Append remaining operations
        while i1 < len(op1):
            result.ops.append(op1[i1])
            i1 += 1
        while i2 < len(op2):
            result.ops.append(op2[i2])
            i2 += 1

        return result

    def compact(self):
        """Compact consecutive operations of the same type."""
        if not self.ops:
            return self

        compacted = []
        last_op = self.ops[0]
        
        for op in self.ops[1:]:
            if isinstance(last_op, str) and isinstance(op, str):
                last_op += op
            elif isinstance(last_op, int) and isinstance(op, int):
                if (last_op < 0 and op < 0) or (last_op > 0 and op > 0):
                    last_op += op
                else:
                    compacted.append(last_op)
                    last_op = op
            else:
                compacted.append(last_op)
                last_op = op
                
        compacted.append(last_op)
        self.ops = compacted
        return self

def compose_operations(op1, op2):
    """Compose two operations into one."""
    if not isinstance(op1, TextOperation) or not isinstance(op2, TextOperation):
        raise TypeError("Both arguments must be TextOperation instances")
    
    composed = op1.compose(op2)
    return composed.compact()