import * as pg from 'pg';
import * as sqlite from 'sqlite3';

type DbConfig = {
	name:		string
	host:		string
	port:		number
	user:		string
	password:	string	
}

interface DbAdapter {
	query:	(s:string, callback:(e:any, rs:any) => void) => void
	close: 	() => void
}

const re_creatematch = /^(CREATE)/i
const re_getmatch = /^(SELECT)/i;
const re_setmatch = /^(INSERT|UPDATE)/i;

class SqliteAdapter implements DbAdapter {

	db:		any

	constructor(dbConfig:DbConfig, callback?:(any) => void) {
		this.db = new sqlite.Database(dbConfig.name); //, callback);
	}

	public query(s:string, callback:(e:any, rs?:any) => void): void {
		const local_callback = (e, rs) => {
			let r = undefined;
			if (rs !== undefined) {
				r = {
					rowCount: rs.length,
					rows: rs,
				}
			}
			callback(e, r);
		};
		if (s.match(re_getmatch)) {
			this.db.all(s, local_callback);
		} else if (s.match(re_setmatch)) {
			this.db.run(s, local_callback);
		} else if (s.match(re_creatematch)) {
			this.db.run(s, callback);
		} else {
			throw 'unhandled query';
		}
	}

	public close() {
		this.db.close();
	}
}

class PostgresAdapter implements DbAdapter {

	db:		any

	constructor(dbConfig:DbConfig) {
		let o = dbConfig;
		o['database'] = o.name;
		this.db = new pg.Pool(o);
		return this.db;
	}

	public query(s:string, callback:(e:any, rs:any) => void): void {
		this.db.query(s, (e, rs) => {
			let r = {
				length: rs.rowCount,
			}
			rs.length = rs.rowCount;
			if (e === undefined) {
				e = null;
			}
			console.debug(e, rs);
			callback(e, rs);
		});
	}

	public close() {
		this.db.end();
	}
}

export {
	DbConfig,
	SqliteAdapter,
	PostgresAdapter,
}
