SELECT * FROM caixinha;
SELECT * FROM categoria;
SELECT * FROM movimentacao;
SELECT * FROM metas;
SELECT * FROM planejado;

SELECT * FROM dim_mov;
SELECT * FROM dim_planejamento;

SELECT * FROM dim_mov WHERE caixinha = 'DIVIDAS';

SELECT
    c.caixinha,
    cat.categoria,
    SUM(p.valor_plan)
FROM planejado p
LEFT JOIN caixinha c ON p.fk_caixinha_id = c.id_caixinha
LEFT JOIN categoria cat ON c.fk_categoria_id = cat.id_categoria
GROUP BY c.caixinha, cat.categoria;

SELECT
    c.caixinha,
    p.descricao_plan,
    SUM(p.valor_plan)
FROM planejado p
LEFT JOIN caixinha c ON p.fk_caixinha_id = c.id_caixinha
GROUP BY p.descricao_plan, c.caixinha
ORDER BY c.caixinha;

UPDATE planejado SET valor_plan = '1377' WHERE id_plan = 10;

UPDATE movimentacao SET status_mov = 'CONFIRMADO';

UPDATE planejado
SET descricao_plan = 'CACHORRO TRATAMENTO',
    recorrencia_plan = 'UNICO'
WHERE id_plan = 20;

INSERT INTO caixinha (caixinha, tipo_caixinha, fk_categoria_id)
VALUES ('TRANSPORTE', 'SAIDA', 6);

UPDATE planejado SET valor_plan = 0 WHERE id_plan = 50;

SELECT *
FROM dim_mov
WHERE pessoa = 'Casal';

SELECT *
FROM dim_planejamento
WHERE pessoa IN ('PJ Stefane', 'PJ Hianara');


