import ass_tag_parser.common
import parsimonious


GRAMMAR_TEXT = (ass_tag_parser.common.DATA_DIR / 'draw_bnf.txt').read_text()
GRAMMAR = parsimonious.Grammar(GRAMMAR_TEXT)


class NodeVisitor(parsimonious.NodeVisitor):
    def generic_visit(self, _node, visited_nodes):
        return visited_nodes

    def visit_draw_commands(self, _node, visited_nodes):
        return ass_tag_parser.common.flatten(visited_nodes)

    def visit_draw_command(self, _node, visited_nodes):
        return visited_nodes

    def visit_pos(self, node, _visited_nodes):
        return int(node.text)

    def visit_draw_command_move(self, _node, visited_nodes):
        return {
            'type': 'move',
            'x': visited_nodes[2],
            'y': visited_nodes[4],
        }

    def visit_draw_command_move_no_close(self, _node, visited_nodes):
        return {
            'type': 'move-no-close',
            'x': visited_nodes[2],
            'y': visited_nodes[4],
        }

    def visit_draw_command_line(self, _node, visited_nodes):
        return {
            'type': 'line',
            'points': [
                {'x': item[1], 'y': item[3]}
                for item in visited_nodes[1]
            ],
        }

    def visit_draw_command_bezier(self, _node, visited_nodes):
        return {
            'type': 'bezier',
            'points': [
                {'x': visited_nodes[2], 'y': visited_nodes[4]},
                {'x': visited_nodes[6], 'y': visited_nodes[8]},
                {'x': visited_nodes[10], 'y': visited_nodes[12]},
            ],
        }

    def visit_draw_command_cubic_spline(self, _node, visited_nodes):
        return {
            'type': 'cubic-bspline',
            'points': [
                {'x': visited_nodes[2], 'y': visited_nodes[4]},
                {'x': visited_nodes[6], 'y': visited_nodes[8]}
            ] + [
                {'x': item[1], 'y': item[3]}
                for item in visited_nodes[9]
            ],
        }

    def visit_draw_command_extend_spline(self, _node, visited_nodes):
        return {
            'type': 'extend-bspline',
            'points': [
                {'x': item[1], 'y': item[3]}
                for item in visited_nodes[1]
            ],
        }

    def visit_draw_command_close_spline(self, _node, _visited_nodes):
        return {'type': 'close-bspline'}


class Serializer:
    def visit(self, draw_commands):
        ret = []
        for item in draw_commands:
            if 'type' not in item:
                raise ass_tag_parser.common.ParsingError(
                    'Item has no type')

            try:
                visiter = getattr(
                    self, 'visit_' + item['type'].replace('-', '_'))
            except AttributeError:
                raise ass_tag_parser.common.ParsingError(
                    'Unknown type %r' % item['type'])

            try:
                result = visiter(item)
            except (IndexError, KeyError, ValueError) as ex:
                raise ass_tag_parser.common.ParsingError(ex)

            ret.append(' '.join(str(item) for item in result))
        return ' '.join(ret)

    def visit_move(self, item):
        return ('m', int(item['x']), int(item['y']))

    def visit_move_no_close(self, item):
        return ('n', int(item['x']), int(item['y']))

    def visit_line(self, item):
        return ('l', *sum([
            (int(point['x']), int(point['y']))
            for point in item['points']], ())
    )

    def visit_bezier(self, item):
        if len(item['points']) < 3:
            raise ValueError('Too few points in Bezier path')
        if len(item['points']) > 3:
            raise ValueError('Too many points in Bezier path')
        return (
            'b',
            item['points'][0]['x'], item['points'][0]['y'],
            item['points'][1]['x'], item['points'][1]['y'],
            item['points'][2]['x'], item['points'][2]['y'])

    def visit_cubic_bspline(self, item):
        if len(item['points']) < 3:
            raise ValueError('Too few points in cubic b-spline')
        return ('s', *sum([
            (int(point['x']), int(point['y']))
            for point in item['points']], ()))

    def visit_extend_bspline(self, item):
        return ('p', *sum([
            (int(point['x']), int(point['y']))
            for point in item['points']], ()))

    def visit_close_bspline(self, item):
        return ('c',)



def parse_draw_commands(text):
    try:
        node = GRAMMAR.parse(text)
        return NodeVisitor().visit(node)
    except parsimonious.exceptions.ParseError as ex:
        raise ass_tag_parser.common.ParsingError(ex)


def serialize_draw_commands(commands):
    return Serializer().visit(commands)
