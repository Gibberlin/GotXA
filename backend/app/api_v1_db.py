#!/usr/bin/env python3
"""
GOTXA SIEM/SOAR REST API - Database CRUD Endpoints
Provides generic database listing, schema inspection, CRUD operations, and raw SQL queries.
"""

from flask import Blueprint, request, jsonify, g
from datetime import datetime
from sqlalchemy import text
import uuid

from app.models import db
from app.auth import authenticate, error_response, success_response, list_response

api = Blueprint('db_api', __name__, url_prefix='/api/db')

@api.route('/tables', methods=['GET'])
@authenticate
def list_tables():
    """Lists all user tables in public schema along with row counts."""
    try:
        query = text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
              AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)
        result = db.session.execute(query)
        tables = [row[0] for row in result]
        
        tables_data = []
        for table in tables:
            count_query = text(f'SELECT COUNT(*) FROM "{table}"')
            count_res = db.session.execute(count_query)
            row_count = count_res.scalar()
            tables_data.append({
                'name': table,
                'count': row_count
            })
            
        return success_response(tables_data)
    except Exception as e:
        db.session.rollback()
        return error_response('DatabaseError', str(e), 500)

@api.route('/tables/<table_name>', methods=['GET'])
@authenticate
def get_table_details(table_name):
    """Returns columns schema and paginated rows for a table."""
    try:
        # Validate table exists to prevent SQL injection
        check_query = text("""
            SELECT EXISTS (
                SELECT 1 
                FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name = :table_name
            )
        """)
        exists = db.session.execute(check_query, {'table_name': table_name}).scalar()
        if not exists:
            return error_response('NotFound', f'Table {table_name} not found', 404)
        
        # Get primary keys
        pk_query = text("""
            SELECT kcu.column_name 
            FROM information_schema.table_constraints tc 
            JOIN information_schema.key_column_usage kcu 
              ON tc.constraint_name = kcu.constraint_name 
             AND tc.table_schema = kcu.table_schema
            WHERE tc.constraint_type = 'PRIMARY KEY' 
              AND tc.table_name = :table_name
        """)
        pk_res = db.session.execute(pk_query, {'table_name': table_name})
        primary_keys = [row[0] for row in pk_res]
        
        # Get column schema info
        cols_query = text("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = :table_name
            ORDER BY ordinal_position
        """)
        cols_res = db.session.execute(cols_query, {'table_name': table_name})
        columns = []
        for col in cols_res:
            col_name = col[0]
            columns.append({
                'name': col_name,
                'type': col[1],
                'nullable': col[2] == 'YES',
                'default': col[3],
                'is_pk': col_name in primary_keys
            })
            
        # Get paginated data
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 20))
        offset = (page - 1) * page_size
        
        # Get total row count
        count_query = text(f'SELECT COUNT(*) FROM "{table_name}"')
        total = db.session.execute(count_query).scalar()
        
        # Select rows
        select_query_str = f'SELECT * FROM "{table_name}"'
        if primary_keys:
            pk_order = ", ".join([f'"{pk}"' for pk in primary_keys])
            select_query_str += f' ORDER BY {pk_order}'
        select_query_str += f' LIMIT :limit OFFSET :offset'
        
        rows_res = db.session.execute(text(select_query_str), {'limit': page_size, 'offset': offset})
        
        rows = []
        for row in rows_res:
            try:
                row_dict = dict(row._mapping)
            except AttributeError:
                row_dict = dict(zip(row.keys(), row))
            
            # Serialize special objects to strings for JSON compatibility
            for k, v in row_dict.items():
                if isinstance(v, datetime):
                    row_dict[k] = v.isoformat()
                elif hasattr(v, 'hex'):  # UUID
                    row_dict[k] = str(v)
                elif isinstance(v, (dict, list)):
                    # Already dict or list, fine
                    pass
            rows.append(row_dict)
            
        return success_response({
            'columns': columns,
            'primary_keys': primary_keys,
            'data': list_response(rows, total, page, page_size)
        })
    except Exception as e:
        db.session.rollback()
        return error_response('DatabaseError', str(e), 500)

@api.route('/tables/<table_name>', methods=['POST'])
@authenticate
def insert_row(table_name):
    """Inserts a new row into the table."""
    try:
        data = request.json
        if not data:
            return error_response('BadRequest', 'No data provided', 400)
            
        # Validate table exists
        check_query = text("""
            SELECT EXISTS (
                SELECT 1 
                FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name = :table_name
            )
        """)
        exists = db.session.execute(check_query, {'table_name': table_name}).scalar()
        if not exists:
            return error_response('NotFound', f'Table {table_name} not found', 404)
            
        columns_str = ", ".join([f'"{k}"' for k in data.keys()])
        placeholders_str = ", ".join([f":{k}" for k in data.keys()])
        
        insert_query = text(f'INSERT INTO "{table_name}" ({columns_str}) VALUES ({placeholders_str})')
        db.session.execute(insert_query, data)
        db.session.commit()
        
        return success_response(message=f'Row successfully inserted into {table_name}')
    except Exception as e:
        db.session.rollback()
        return error_response('DatabaseError', str(e), 400)

@api.route('/tables/<table_name>', methods=['PUT'])
@authenticate
def update_row(table_name):
    """Updates an existing row matching primary key filters."""
    try:
        body = request.json
        if not body:
            return error_response('BadRequest', 'No body provided', 400)
            
        pk = body.get('pk', {})
        data = body.get('data', {})
        
        if not pk or not data:
            return error_response('BadRequest', 'Missing pk or data in request body', 400)
            
        # Validate table exists
        check_query = text("""
            SELECT EXISTS (
                SELECT 1 
                FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name = :table_name
            )
        """)
        exists = db.session.execute(check_query, {'table_name': table_name}).scalar()
        if not exists:
            return error_response('NotFound', f'Table {table_name} not found', 404)
            
        set_clauses = ", ".join([f'"{k}" = :data_{k}' for k in data.keys()])
        where_clauses = " AND ".join([f'"{k}" = :pk_{k}' for k in pk.keys()])
        
        params = {}
        for k, v in data.items():
            params[f'data_{k}'] = v
        for k, v in pk.items():
            params[f'pk_{k}'] = v
            
        update_query = text(f'UPDATE "{table_name}" SET {set_clauses} WHERE {where_clauses}')
        result = db.session.execute(update_query, params)
        db.session.commit()
        
        return success_response(message=f'Updated {result.rowcount} row(s) in {table_name}')
    except Exception as e:
        db.session.rollback()
        return error_response('DatabaseError', str(e), 400)

@api.route('/tables/<table_name>', methods=['DELETE'])
@authenticate
def delete_row(table_name):
    """Deletes an existing row matching primary key filters."""
    try:
        body = request.json
        if not body:
            return error_response('BadRequest', 'No body provided', 400)
            
        pk = body.get('pk', {})
        if not pk:
            return error_response('BadRequest', 'Missing pk in request body', 400)
            
        # Validate table exists
        check_query = text("""
            SELECT EXISTS (
                SELECT 1 
                FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name = :table_name
            )
        """)
        exists = db.session.execute(check_query, {'table_name': table_name}).scalar()
        if not exists:
            return error_response('NotFound', f'Table {table_name} not found', 404)
            
        where_clauses = " AND ".join([f'"{k}" = :pk_{k}' for k in pk.keys()])
        params = {f'pk_{k}': v for k, v in pk.items()}
        
        delete_query = text(f'DELETE FROM "{table_name}" WHERE {where_clauses}')
        result = db.session.execute(delete_query, params)
        db.session.commit()
        
        return success_response(message=f'Deleted {result.rowcount} row(s) from {table_name}')
    except Exception as e:
        db.session.rollback()
        return error_response('DatabaseError', str(e), 400)

@api.route('/query', methods=['POST'])
@authenticate
def execute_custom_query():
    """Executes a custom raw SQL query."""
    try:
        body = request.json
        query_str = body.get('query')
        params = body.get('params', {})
        
        if not query_str:
            return error_response('BadRequest', 'No query provided', 400)
            
        result = db.session.execute(text(query_str), params)
        
        if result.returns_rows:
            columns = list(result.keys())
            rows = []
            for row in result:
                try:
                    row_dict = dict(row._mapping)
                except AttributeError:
                    row_dict = dict(zip(row.keys(), row))
                    
                for k, v in row_dict.items():
                    if isinstance(v, datetime):
                        row_dict[k] = v.isoformat()
                    elif hasattr(v, 'hex'):  # UUID
                        row_dict[k] = str(v)
                    elif isinstance(v, (dict, list)):
                        # Already dict or list, fine
                        pass
                rows.append(row_dict)
                
            db.session.commit()
            return success_response({
                'columns': columns,
                'rows': rows,
                'returns_rows': True
            })
        else:
            db.session.commit()
            return success_response({
                'rowcount': result.rowcount,
                'returns_rows': False
            })
    except Exception as e:
        db.session.rollback()
        return error_response('SQLError', str(e), 400)
