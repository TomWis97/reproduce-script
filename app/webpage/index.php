<html>
    <head>
        <title>PHP Info Test.</title>
    </head>
    <body>
        <h1>PHP Info demo</h1>
        <p>Dit is een test voor source2image.</p>
        <h2>Environment variables</h2>
        <table>
            <tr>
                <th>PHPAPPDATA</th><td><?php echo $_ENV['PHPAPPDATA'] ?></td>
            </tr>
        </table>
        <?php
            phpinfo();
        ?>
    </body>
</html>
