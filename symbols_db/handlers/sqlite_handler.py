import datetime
import os
import sqlite3
from symbols_db import DEBUG_MODE, BLINTDB_LOCATION
from pathlib import PurePath

connection = sqlite3.connect(BLINTDB_LOCATION)


def set_global_connection():
    global connection
    connection = sqlite3.connect(BLINTDB_LOCATION)


def start_connection():
    if not "connection" in globals():
        set_global_connection()
    c = connection.cursor()
    return c


def create_database():
    c = start_connection()

    # TODO: not as required
    # blintsboms = c.execute(
    #     """
    #      CREATE TABLE IF NOT EXISTS blintsboms (
    #         purl    VARCHAR(100),
    #         time    timestamp,
    #         sbom    BLOB
    #     );
    #     """
    # )
    projects_table = c.execute(
        """
        CREATE TABLE IF NOT EXISTS Projects (
            pid     INTEGER PRIMARY KEY AUTOINCREMENT,
            pname   VARCHAR(255) UNIQUE,
            purl    VARCHAR(255),
            cbom    BLOB
        );
        """
    )

    binaries_table = c.execute(
        """
        CREATE TABLE IF NOT EXISTS Binaries (
            bid     INTEGER PRIMARY KEY AUTOINCREMENT,
            pid     INTEGER,
            bname   VARCHAR(500),
            bbom    BLOB,
                     
            FOREIGN KEY (pid) REFERENCES Projects(pid)
        );
        """
    )

    exports_table = c.execute(
        """
        CREATE TABLE IF NOT EXISTS Exports (
            infunc  VARCHAR(255) PRIMARY KEY
        );
        """
    )
    binary_exports_tabel = c.execute(
        """
        CREATE TABLE IF NOT EXISTS BinariesExports (
            bid INTEGER,
            eid INTEGER,
            PRIMARY KEY (bid, eid),
            FOREIGN KEY (bid) REFERENCES Binaries(bid),
            FOREIGN KEY (eid) REFERENCES Exports(eid)
        );
        """
    )

    index_table = c.execute(
        """
        CREATE INDEX IF NOT EXISTS export_name_index ON Exports (infunc);
        """
    )
    if DEBUG_MODE:
        # print(blintsboms, projects_table, binaries_table, exports_table, index_table)
        print(
            projects_table,
            binaries_table,
            exports_table,
            binary_exports_tabel,
            index_table,
        )
    connection.commit()


def clear_sqlite_database():
    global connection
    del connection
    os.remove(BLINTDB_LOCATION)


def store_sbom_in_sqlite(purl, sbom):
    c = start_connection()
    c.execute(
        "INSERT INTO blintsboms VALUES (?, ?, jsonb(?))",
        (purl, datetime.datetime.now(), sbom),
    )
    connection.commit()


# add project
def add_projects(project_name, purl=None, cbom=None):
    c = start_connection()
    c.execute(
        "INSERT INTO Projects (pname, purl, cbom) VALUES (?, ?, ?)",
        (project_name, purl, cbom),
    )
    connection.commit()

    # retrieve pid
    c.execute("SELECT pid FROM Projects WHERE pname=?", (project_name,))
    res = c.fetchall()

    connection.commit()
    return res[0][0]


# add binary
def add_binary(binary_file_path, project_id, blint_bom=None):
    if isinstance(binary_file_path, PurePath):
        binary_file_path = str(binary_file_path)

    # truncate the binary file path
    binary_file_path = binary_file_path.split("subprojects/")[1]

    c = start_connection()
    c.execute(
        "INSERT INTO Binaries (pid, bname, bbom) VALUES (?, ?, ?)",
        (project_id, binary_file_path, blint_bom),
    )
    connection.commit()

    # retrieve bid
    c.execute("SELECT bid FROM Binaries WHERE bname=?", (binary_file_path,))
    res = c.fetchall()
    connection.commit()
    return res[0][0]


# add export
def add_binary_export(infunc, bid):

    def _fetch_bin_exists(bid, eid):
        c.execute("SELECT bid FROM BinariesExports WHERE bid=? and eid=?", (bid, eid))
        res = c.fetchall()[0][0]
        connection.commit()
        if res == bid:
            return True
        else:
            return False

    def _fetch_infunc_row(infunc):
        c.execute("SELECT rowid FROM Exports WHERE infunc=?", (infunc,))
        res = c.fetchall()
        connection.commit()
        return res

    c = start_connection()
    pre_existing = _fetch_infunc_row(infunc)
    if pre_existing:
        eid = pre_existing[0][0]
        if _fetch_bin_exists(bid, eid):
            c.execute(
                "INSERT INTO BinariesExports (bid, eid) VALUES (?, ?)", (bid, eid)
            )
            connection.commit()
        return 0

    c.execute("INSERT INTO Exports (infunc) VALUES (?)", (infunc,))
    connection.commit()

    eid = _fetch_infunc_row(infunc)[0][0]

    c.execute("INSERT INTO BinariesExports (bid, eid) VALUES (?, ?)", (bid, eid))
    connection.commit()


# create the sqlite tables
create_database()
