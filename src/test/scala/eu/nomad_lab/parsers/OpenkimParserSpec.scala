package eu.nomad_lab.parsers

import org.specs2.mutable.Specification

object OpenkimParserTests extends Specification {
  "OpenkimParserTest" >> {
    "[OpenKIM Query with 3767 entries] test with json-events" >> {
      ParserRun.parse(OpenkimParser, "parsers/openkim/test/examples/data.json", "json-events") must_== ParseResult.ParseSuccess
    }
    "[OpenKIM Query with 3767 entries] test with json" >> {
      ParserRun.parse(OpenkimParser, "parsers/openkim/test/examples/data.json", "json") must_== ParseResult.ParseSuccess
    }
  }
}
